import { computed, getCurrentInstance, onBeforeUnmount, ref } from 'vue'

/**
 * Browser speech recognition for the optional speaking mode (D-087). The browser (not Master Mentor) turns speech
 * into text; in some browsers the audio is processed by the browser vendor's speech service. Master Mentor never
 * records, uploads or stores audio: only the transcript text the learner submits is sent.
 */
export interface RecognitionResultLike {
  isFinal: boolean
  0: { transcript: string }
}
export interface RecognitionEventLike {
  resultIndex: number
  results: { length: number; [index: number]: RecognitionResultLike }
}
export interface RecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: RecognitionEventLike) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
  abort(): void
}
export type RecognitionConstructor = new () => RecognitionLike

export const SPEECH_UNSUPPORTED = "Speech practice isn't supported in this browser."
export const SPEECH_DISCLOSURE =
  "Speech recognition is provided by your browser's speech service. Master Mentor does not store audio. " +
  'Only the transcript text you choose to submit is saved.'

const ERROR_TEXT: Record<string, string> = {
  'not-allowed': 'Microphone access was blocked. Allow it for this site, or use manual practice.',
  'service-not-allowed': 'Your browser blocked speech recognition. Use manual practice instead.',
  'no-speech': 'No speech was heard. Check your microphone and try again.',
  'audio-capture': 'No microphone was found. Use manual practice instead.',
  network: "The browser's speech service could not be reached. Use manual practice instead.",
}

export function findRecognition(scope: Record<string, unknown> = window as unknown as Record<string, unknown>): RecognitionConstructor | null {
  const ctor = scope.SpeechRecognition ?? scope.webkitSpeechRecognition
  return typeof ctor === 'function' ? (ctor as RecognitionConstructor) : null
}

export function useSpeechRecognition(ctor: RecognitionConstructor | null = findRecognition(), now: () => number = Date.now) {
  const supported = ctor !== null
  const listening = ref(false)
  const final = ref('')
  const interim = ref('')
  const error = ref('')
  const elapsed = ref(0)
  let recognition: RecognitionLike | null = null
  let wantListening = false
  let startedAt = 0
  let timer: ReturnType<typeof setInterval> | undefined

  const transcript = computed(() => `${final.value} ${interim.value}`.trim())

  function clear(): void {
    if (timer) clearInterval(timer)
    timer = undefined
  }

  function start(): void {
    if (!ctor || listening.value) return
    error.value = ''
    final.value = ''
    interim.value = ''
    recognition = new ctor()
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event) => {
      let live = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const part = event.results[i]
        if (!part) continue
        if (part.isFinal) final.value = `${final.value} ${part[0].transcript}`.trim()
        else live += part[0].transcript
      }
      interim.value = live
    }
    recognition.onerror = (event) => {
      error.value = ERROR_TEXT[event.error] ?? `Speech recognition stopped (${event.error}).`
      if (event.error !== 'no-speech') wantListening = false
    }
    recognition.onend = () => {
      if (wantListening && recognition) {
        try {
          recognition.start() // browsers end a session after a pause; continue until the learner stops
          return
        } catch {
          wantListening = false
        }
      }
      listening.value = false
      clear()
    }
    wantListening = true
    startedAt = now()
    elapsed.value = 0
    timer = setInterval(() => (elapsed.value = Math.max(0, Math.floor((now() - startedAt) / 1000))), 500)
    listening.value = true
    recognition.start()
  }

  function stop(): void {
    wantListening = false
    elapsed.value = Math.max(0, Math.floor((now() - startedAt) / 1000))
    recognition?.stop()
    listening.value = false
    final.value = transcript.value
    interim.value = ''
    clear()
  }

  if (getCurrentInstance()) {
    onBeforeUnmount(() => {
      wantListening = false
      recognition?.abort()
      clear()
    })
  }

  return { supported, listening, transcript, final, interim, error, elapsed, start, stop }
}
