import mixpanel from "mixpanel-browser";

const TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
let initialized = false;

export function initMixpanel() {
  if (!TOKEN || initialized) return;
  mixpanel.init(TOKEN, {
    persistence: "localStorage",
    track_pageview: false,
    ignore_dnt: false,
  });
  initialized = true;
}

export function trackEvent(
  event: string,
  properties?: Record<string, unknown>
) {
  if (!TOKEN || !initialized) return;
  mixpanel.track(event, properties);
}

export function trackPageView(url: string) {
  if (!TOKEN || !initialized) return;
  mixpanel.track("Page View", { url });
}

export function identifyUser(
  userId: string,
  traits?: Record<string, unknown>
) {
  if (!TOKEN || !initialized) return;
  mixpanel.identify(userId);
  if (traits) {
    mixpanel.people.set(traits);
  }
}

export function resetUser() {
  if (!TOKEN || !initialized) return;
  mixpanel.reset();
}
