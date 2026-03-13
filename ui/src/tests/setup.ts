import "@testing-library/jest-dom";

// jsdom can be configured with a missing --localstorage-file path, which leaves
// window.localStorage without the standard methods. Provide a working in-memory
// implementation so any component that uses localStorage works in tests.
const _localStorageStore: Record<string, string> = {};
const localStorageMock: Storage = {
  getItem: (key) => _localStorageStore[key] ?? null,
  setItem: (key, value) => { _localStorageStore[key] = String(value); },
  removeItem: (key) => { delete _localStorageStore[key]; },
  clear: () => { Object.keys(_localStorageStore).forEach((k) => delete _localStorageStore[k]); },
  get length() { return Object.keys(_localStorageStore).length; },
  key: (index) => Object.keys(_localStorageStore)[index] ?? null,
};
Object.defineProperty(window, "localStorage", { value: localStorageMock, writable: true });

// jsdom does not implement ResizeObserver. Provide a no-op stub so components
// that use it (e.g. the header spacer sync) don't crash in tests.
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// @base-ui/react ScrollArea calls element.getAnimations() in a timeout.
// jsdom doesn't implement it, causing an unhandled exception after tests complete.
if (!Element.prototype.getAnimations) {
  Element.prototype.getAnimations = () => [];
}
