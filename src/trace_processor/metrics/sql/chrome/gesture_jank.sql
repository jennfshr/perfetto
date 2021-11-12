--
-- Copyright 2021 The Android Open Source Project
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- A collection of templated metrics related to continuous motion gestures that
-- have start, end and update events.
--
-- We define an update to be janky if comparing forwards or backwards (ignoring
-- coalesced updates) a given updates exceeds the duration of its predecessor or
-- successor by 50% of a vsync interval (defaulted to 60 FPS).
--
-- WARNING: This metric should not be used as a source of truth. It is under
--          active development and the values & meaning might change without
--          notice.

-- Get all chrome processes and threads tables set up.
SELECT RUN_METRIC('chrome/chrome_processes.sql');

-- When working on InputLatency events we need to ensure we have all the events
-- from the browser, renderer, and GPU processes. This query isn't quite
-- perfect. In system tracing we could have 3 browser processes all in the
-- background and this would match, but for now its the best we can do (renderer
-- and GPU names on android are quite complicated, but this should filter 99%
-- (citation needed) of what we want.
--
-- See b/151077536 for historical context.
-- TODO(b/197841224): Refactor or remove this table.
DROP VIEW IF EXISTS sufficient_chrome_processes;
CREATE VIEW sufficient_chrome_processes AS
  SELECT
    CASE WHEN (
      SELECT COUNT(*) FROM chrome_process) = 0
    THEN
      FALSE
    ELSE (
      SELECT COUNT(*) >= 3 FROM (
        SELECT name FROM chrome_process
        WHERE
          name GLOB "Browser" OR
          name GLOB "Renderer" OR
          name GLOB "Gpu" OR
          name GLOB 'com.android.chrome*' OR
          name GLOB 'com.chrome.beta*' OR
          name GLOB 'com.chrome.dev*' OR
          name GLOB 'com.chrome.canary*' OR
          name GLOB 'com.google.android.apps.chrome*' OR
          name GLOB 'org.chromium.chrome*'
        GROUP BY name
    )) END AS have_enough_chrome_processes;

-- A simple table that checks the time between VSync (this can be used to
-- determine if we're refreshing at 90 FPS or 60 FPS.
--
-- Note: In traces without the "Java" category there will be no VSync
--       TraceEvents and this table will be empty.
--
-- Note: Must be a TABLE because it uses a window function which can behave
--       strangely in views.
DROP TABLE IF EXISTS vsync_intervals;
CREATE TABLE vsync_intervals AS
  SELECT
    slice_id,
    ts,
    dur,
    track_id,
    LEAD(ts) OVER(PARTITION BY track_id ORDER BY ts) - ts AS time_to_next_vsync
  FROM slice
  WHERE name = "VSync"
  ORDER BY track_id, ts;

-- Get all the "begin" and "end" events. We take their IDs to group them
-- together into gestures later and the timestamp and duration to compute the
-- duration of the gesture.
DROP VIEW IF EXISTS {{prefix}}_begin_and_end;
CREATE VIEW {{prefix}}_begin_and_end AS
  SELECT
    slice.name,
    slice.id,
    slice.ts,
    slice.dur,
    slice.track_id,
    EXTRACT_ARG(arg_set_id, 'chrome_latency_info.{{id_field}}')
        AS {{id_field}},
    EXTRACT_ARG(arg_set_id, "chrome_latency_info.trace_id") AS trace_id
  FROM
    slice
  WHERE
    slice.name IN (
      'InputLatency::{{gesture_start}}',
      'InputLatency::{{gesture_end}}'
    )
  ORDER BY ts;

-- Now we take the "begin" and the "end" events and join the information into a
-- single row per gesture. We also compute the average Vysnc interval of the
-- gesture (hopefully this would be either 60 FPS for the whole gesture or 90
-- FPS but that isn't always the case). If the trace doesn't contain the VSync
-- TraceEvent we just fall back on assuming its 60 FPS (this is the 1.6e+7 in
-- the COALESCE which corresponds to 16 ms or 60 FPS).
DROP VIEW IF EXISTS joined_{{prefix}}_begin_and_end;
CREATE VIEW joined_{{prefix}}_begin_and_end AS
  SELECT
    begin.id AS begin_id,
    begin.ts AS begin_ts,
    begin.dur AS begin_dur,
    begin.track_id AS begin_track_id,
    begin.trace_id AS begin_trace_id,
    COALESCE(begin.{{id_field}}, begin.trace_id)
        AS begin_{{id_field}},
    end.ts AS end_ts,
    end.ts + end.dur AS end_ts_and_dur,
    end.trace_id AS end_trace_id,
    COALESCE((
      SELECT
        CAST(AVG(time_to_next_vsync) AS FLOAT)
      FROM vsync_intervals in_query
      WHERE
        time_to_next_vsync IS NOT NULL AND
        in_query.ts > begin.ts AND
        in_query.ts < end.ts
    ), 1e+9 / 60) AS avg_vsync_interval
  FROM {{prefix}}_begin_and_end begin JOIN {{prefix}}_begin_and_end end ON
    begin.trace_id < end.trace_id AND
    begin.name = 'InputLatency::{{gesture_start}}' AND
    end.name = 'InputLatency::{{gesture_end}}' AND (
      (
        begin.{{id_field}} IS NULL AND
        end.trace_id = (
          SELECT MIN(trace_id)
          FROM {{prefix}}_begin_and_end in_query
          WHERE
            name = 'InputLatency::{{gesture_end}}' AND
          in_query.trace_id > begin.trace_id
        )
      ) OR
      end.{{id_field}} = begin.{{id_field}}
    )
  ORDER BY begin.ts;

-- Get the "update" events by name ordered by the |{{id_field}}|, and
-- timestamp. Then compute the number of frames (relative to vsync interval)
-- that each event took. 1.6e+7 is 16 ms in nanoseconds and is used in case
-- there are no VSync events to default to 60 fps. We join each
-- {{gesture_update}} event to the information about its "begin" and "end"
-- events for easy computation later.
--
-- We remove updates with |dur| == -1 because this means we have no "end" event
-- and can't reasonably determine what it should be. We have separate tracking
-- to ensure this only happens at the end of the trace where its expected.
--
-- Note: Must be a TABLE because it uses a window function which can behave
--       strangely in views.
DROP TABLE IF EXISTS {{id_field}}_update;
CREATE TABLE {{id_field}}_update AS
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY {{id_field}} ASC, ts ASC) AS row_number,
    begin_id,
    begin_ts,
    begin_dur,
    begin_track_id,
    begin_trace_id,
    COALESCE({{id_field}}, begin_trace_id) AS {{id_field}},
    CASE WHEN
      end_ts_and_dur > ts + dur THEN
        end_ts_and_dur
      ELSE
        ts + dur
      END AS maybe_gesture_end,
    id,
    ts,
    dur,
    track_id,
    trace_id,
    dur/avg_vsync_interval AS gesture_frames_exact
  FROM joined_{{prefix}}_begin_and_end begin_and_end JOIN (
    SELECT
      EXTRACT_ARG(arg_set_id, "chrome_latency_info.trace_id") AS trace_id,
      EXTRACT_ARG(arg_set_id, 'chrome_latency_info.{{id_field}}')
          AS {{id_field}},
      *
    FROM
      slice JOIN track ON slice.track_id = track.id
    WHERE
      slice.name = 'InputLatency::{{gesture_update}}' AND
      slice.dur != -1 AND
      NOT COALESCE(
              EXTRACT_ARG(arg_set_id, "chrome_latency_info.is_coalesced"),
              TRUE)
      AND slice.arg_set_id IN (
        SELECT arg_set_id
        FROM args
        WHERE args.arg_set_id = slice.arg_set_id
        AND flat_key = 'chrome_latency_info.component_info.component_type'
        AND string_value = 'COMPONENT_INPUT_EVENT_GPU_SWAP_BUFFER'
      )
  ) gesture_update ON
  gesture_update.ts <= begin_and_end.end_ts AND
  gesture_update.ts >= begin_and_end.begin_ts AND
  gesture_update.trace_id > begin_and_end.begin_trace_id AND
  gesture_update.trace_id < begin_and_end.end_trace_id AND (
    gesture_update.{{id_field}} IS NULL OR
    gesture_update.{{id_field}} = begin_and_end.begin_{{id_field}}
  );

-- This takes the "update" events and joins it to the previous "update" event
-- (previous row and NULL if there isn't one) and the next "update" event (next
-- row and again NULL if there isn't one). Then we compute the duration of the
-- event (relative to fps) and see if it increased by more than 0.5 (which is
-- 1/2 of 16 ms at 60 fps, and so on).
--
-- A small number is added to 0.5 in order to make sure that the comparison does
-- not filter out ratios that are precisely 0.5, which can fall a little above
-- or below exact value due to inherent inaccuracy of operations with
-- floating-point numbers. Value 1e-9 have been chosen as follows: the ratio has
-- nanoseconds in numerator and VSync interval in denominator. Assuming refresh
-- rate more than 1 FPS (and therefore VSync interval less than a second), this
-- ratio should increase with increments more than minimal value in numerator
-- (1ns) divided by maximum value in denominator, giving 1e-9.
--
--
-- We only compare an "update" event to another event within the same gesture
-- ({{id_field}} == prev/next {{id_field}}). This controls somewhat for
-- variability of gestures.
--
-- Note: Must be a TABLE because it uses a window function which can behave
--       strangely in views.
DROP TABLE IF EXISTS {{prefix}}_jank_maybe_null_prev_and_next;
CREATE TABLE {{prefix}}_jank_maybe_null_prev_and_next AS
  SELECT
    currprev.*,
    CASE WHEN
      currprev.{{id_field}} != prev_{{id_field}} OR
      prev_ts IS NULL OR
      prev_ts < currprev.begin_ts OR
      prev_ts > currprev.maybe_gesture_end
    THEN
      FALSE
    ELSE
      currprev.gesture_frames_exact > prev_gesture_frames_exact + 0.5 + 1e-9
    END AS prev_jank,
    CASE WHEN
      currprev.{{id_field}} != next.{{id_field}} OR
      next.ts IS NULL OR
      next.ts < currprev.begin_ts OR
      next.ts > currprev.maybe_gesture_end
    THEN
      FALSE
    ELSE
      currprev.gesture_frames_exact > next.gesture_frames_exact + 0.5 + 1e-9
    END AS next_jank,
    next.gesture_frames_exact AS next_gesture_frames_exact
  FROM (
    SELECT
      curr.*,
      curr.maybe_gesture_end - curr.begin_ts AS {{prefix}}_dur,
      prev.ts AS prev_ts,
      prev.{{id_field}} AS prev_{{id_field}},
      prev.gesture_frames_exact AS prev_gesture_frames_exact
    FROM
      {{id_field}}_update curr LEFT JOIN
      {{id_field}}_update prev ON prev.row_number + 1 = curr.row_number
  ) currprev LEFT JOIN
  {{id_field}}_update next ON currprev.row_number + 1 = next.row_number
  ORDER BY currprev.{{id_field}} ASC, currprev.ts ASC;

-- This just uses prev_jank and next_jank to see if each "update" event is a
-- jank.
DROP VIEW IF EXISTS {{prefix}}_jank;
CREATE VIEW {{prefix}}_jank AS
  SELECT
    id AS slice_id,
    (next_jank IS NOT NULL AND next_jank) OR
    (prev_jank IS NOT NULL AND prev_jank)
    AS jank,
    *
  FROM {{prefix}}_jank_maybe_null_prev_and_next
  ORDER BY {{id_field}} ASC, ts ASC;

DROP VIEW IF EXISTS {{prefix}}_jank_output;
CREATE VIEW {{prefix}}_jank_output AS
  SELECT
    {{proto_name}}(
      '{{prefix}}_jank_percentage', (
        SELECT
          (
            SUM(CASE WHEN jank THEN dur ELSE 0 END)/CAST(SUM(dur) AS REAL)
          ) * 100.0
        FROM {{prefix}}_jank
      ),
      '{{prefix}}_ms', (
        SELECT
          CAST(SUM({{prefix}}_dur)/1e6 AS REAL)
        FROM (
          SELECT
            MAX({{prefix}}_dur) AS {{prefix}}_dur
          FROM {{prefix}}_jank
          GROUP BY {{id_field}}
        )
      ),
      '{{prefix}}_processing_ms', CAST(SUM(dur)/1e6 AS REAL),
      '{{prefix}}_jank_processing_ms', (
        SELECT CAST(SUM(dur)/1e6 AS REAL) FROM {{prefix}}_jank WHERE jank
      ),
      'num_{{prefix}}_update_count', COUNT(*),
      'num_{{prefix}}_update_jank_count', SUM(jank)
    )
  FROM {{prefix}}_jank;
