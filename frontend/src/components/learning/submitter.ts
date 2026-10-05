import type { CompletionInput, CompletionResult, Effects } from '../../api/types'

/** Records a completion: the content endpoint, or a learning-session step. */
export type Submitter = (input: CompletionInput) => Promise<{ result: CompletionResult; effects?: Effects }>
