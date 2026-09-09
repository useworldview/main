// Tool-agnostic analytics stub — wire to a real provider later
// Per frontend spec Section 15.4

export function track(eventName: string, properties?: Record<string, unknown>) {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Analytics] ${eventName}`, properties || '');
  }
  // Wire to your analytics provider here (e.g., Segment, PostHog, Mixpanel)
}
