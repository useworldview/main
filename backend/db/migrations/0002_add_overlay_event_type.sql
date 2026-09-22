-- Migration: Add 'overlay_dismissed' to interaction_events.event_type constraint
-- The overlay dismissal phase logs events with event_type='overlay_dismissed',
-- which was missing from the original CHECK constraint.

ALTER TABLE public.interaction_events
  DROP CONSTRAINT interaction_events_event_type_check;

ALTER TABLE public.interaction_events
  ADD CONSTRAINT interaction_events_event_type_check
  CHECK (event_type IN (
    'click','scroll','type','navigate','search','back','forward',
    'wait','screenshot','form_submit','page_error','dead_end',
    'overlay_dismissed'
  ));
