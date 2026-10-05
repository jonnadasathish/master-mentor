// jsdom does not implement scrolling; the router's scroll behaviour calls it on every navigation.
window.scrollTo = (() => undefined) as typeof window.scrollTo
