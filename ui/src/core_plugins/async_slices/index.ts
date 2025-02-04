// Copyright (C) 2021 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {removeFalsyValues} from '../../base/array_utils';
import {TrackNode} from '../../public/workspace';
import {ASYNC_SLICE_TRACK_KIND} from '../../public/track_kinds';
import {Trace} from '../../public/trace';
import {PerfettoPlugin, PluginDescriptor} from '../../public/plugin';
import {getThreadUriPrefix, getTrackName} from '../../public/utils';
import {NUM, NUM_NULL, STR, STR_NULL} from '../../trace_processor/query_result';
import {AsyncSliceTrack} from './async_slice_track';
import {
  getOrCreateGroupForProcess,
  getOrCreateGroupForThread,
} from '../../public/standard_groups';
import {exists} from '../../base/utils';

class AsyncSlicePlugin implements PerfettoPlugin {
  async onTraceLoad(ctx: Trace): Promise<void> {
    await this.addGlobalAsyncTracks(ctx);
    await this.addProcessAsyncSliceTracks(ctx);
    await this.addThreadAsyncSliceTracks(ctx);
    await this.addUserAsyncSliceTracks(ctx);
  }

  async addGlobalAsyncTracks(ctx: Trace): Promise<void> {
    const {engine} = ctx;
    const rawGlobalAsyncTracks = await engine.query(`
      with global_tracks_grouped as (
        select
          parent_id,
          name,
          group_concat(id) as trackIds,
          count() as trackCount
        from track t
        join _slice_track_summary using (id)
        where t.type in ('__intrinsic_track', 'gpu_track', '__intrinsic_cpu_track')
        group by parent_id, name
      )
      select
        t.name as name,
        t.parent_id as parentId,
        t.trackIds as trackIds,
        __max_layout_depth(t.trackCount, t.trackIds) as maxDepth
      from global_tracks_grouped t
    `);
    const it = rawGlobalAsyncTracks.iter({
      name: STR_NULL,
      parentId: NUM_NULL,
      trackIds: STR,
      maxDepth: NUM,
    });

    // Create a map of track nodes by id
    const trackMap = new Map<
      number,
      {parentId: number | null; trackNode: TrackNode}
    >();

    for (; it.valid(); it.next()) {
      const rawName = it.name === null ? undefined : it.name;
      const title = getTrackName({
        name: rawName,
        kind: ASYNC_SLICE_TRACK_KIND,
      });
      const rawTrackIds = it.trackIds;
      const trackIds = rawTrackIds.split(',').map((v) => Number(v));
      const maxDepth = it.maxDepth;

      const uri = `/async_slices_${rawName}_${it.parentId}`;
      ctx.tracks.registerTrack({
        uri,
        title,
        tags: {
          trackIds,
          kind: ASYNC_SLICE_TRACK_KIND,
          scope: 'global',
        },
        track: new AsyncSliceTrack({trace: ctx, uri}, maxDepth, trackIds),
      });
      const trackNode = new TrackNode({uri, title, sortOrder: -25});
      trackIds.forEach((id) =>
        trackMap.set(id, {parentId: it.parentId, trackNode}),
      );
    }

    // Attach track nodes to parents / or the workspace if they have no parent
    trackMap.forEach((t) => {
      const parent = exists(t.parentId) && trackMap.get(t.parentId);
      if (parent !== false && parent !== undefined) {
        parent.trackNode.addChildInOrder(t.trackNode);
      } else {
        ctx.workspace.addChildInOrder(t.trackNode);
      }
    });
  }

  async addProcessAsyncSliceTracks(ctx: Trace): Promise<void> {
    const result = await ctx.engine.query(`
      select
        upid,
        t.name as trackName,
        t.track_ids as trackIds,
        process.name as processName,
        process.pid as pid,
        t.parent_id as parentId,
        __max_layout_depth(t.track_count, t.track_ids) as maxDepth
      from _process_track_summary_by_upid_and_parent_id_and_name t
      join process using(upid)
      where t.name is null or t.name not glob "* Timeline"
    `);

    const it = result.iter({
      upid: NUM,
      parentId: NUM_NULL,
      trackName: STR_NULL,
      trackIds: STR,
      processName: STR_NULL,
      pid: NUM_NULL,
      maxDepth: NUM,
    });

    const trackMap = new Map<
      number,
      {parentId: number | null; upid: number; trackNode: TrackNode}
    >();

    for (; it.valid(); it.next()) {
      const upid = it.upid;
      const trackName = it.trackName;
      const rawTrackIds = it.trackIds;
      const trackIds = rawTrackIds.split(',').map((v) => Number(v));
      const processName = it.processName;
      const pid = it.pid;
      const maxDepth = it.maxDepth;

      const kind = ASYNC_SLICE_TRACK_KIND;
      const title = getTrackName({
        name: trackName,
        upid,
        pid,
        processName,
        kind,
      });

      const uri = `/process_${upid}/async_slices_${rawTrackIds}`;
      ctx.tracks.registerTrack({
        uri,
        title,
        tags: {
          trackIds,
          kind: ASYNC_SLICE_TRACK_KIND,
          scope: 'process',
          upid,
        },
        track: new AsyncSliceTrack({trace: ctx, uri}, maxDepth, trackIds),
      });
      const track = new TrackNode({uri, title, sortOrder: 30});
      trackIds.forEach((id) =>
        trackMap.set(id, {trackNode: track, parentId: it.parentId, upid}),
      );
    }

    // Attach track nodes to parents / or the workspace if they have no parent
    trackMap.forEach((t) => {
      const parent = exists(t.parentId) && trackMap.get(t.parentId);
      if (parent !== false && parent !== undefined) {
        parent.trackNode.addChildInOrder(t.trackNode);
      } else {
        const processGroup = getOrCreateGroupForProcess(ctx.workspace, t.upid);
        processGroup.addChildInOrder(t.trackNode);
      }
    });
  }

  async addThreadAsyncSliceTracks(ctx: Trace): Promise<void> {
    const result = await ctx.engine.query(`
      include perfetto module viz.summary.slices;
      include perfetto module viz.summary.threads;
      include perfetto module viz.threads;

      select
        t.utid,
        t.parent_id as parentId,
        thread.upid,
        t.name as trackName,
        thread.name as threadName,
        thread.tid as tid,
        t.track_ids as trackIds,
        __max_layout_depth(t.track_count, t.track_ids) as maxDepth,
        k.is_main_thread as isMainThread,
        k.is_kernel_thread AS isKernelThread
      from _thread_track_summary_by_utid_and_name t
      join _threads_with_kernel_flag k using(utid)
      join thread using (utid)
      where t.track_count > 1
    `);

    const it = result.iter({
      utid: NUM,
      parentId: NUM_NULL,
      upid: NUM_NULL,
      trackName: STR_NULL,
      trackIds: STR,
      maxDepth: NUM,
      isMainThread: NUM_NULL,
      isKernelThread: NUM,
      threadName: STR_NULL,
      tid: NUM_NULL,
    });

    const trackMap = new Map<
      number,
      {parentId: number | null; utid: number; trackNode: TrackNode}
    >();

    for (; it.valid(); it.next()) {
      const {
        utid,
        parentId,
        upid,
        trackName,
        isMainThread,
        isKernelThread,
        maxDepth,
        threadName,
        tid,
      } = it;
      const rawTrackIds = it.trackIds;
      const trackIds = rawTrackIds.split(',').map((v) => Number(v));
      const title = getTrackName({
        name: trackName,
        utid,
        tid,
        threadName,
        kind: 'Slices',
      });

      const uri = `/${getThreadUriPrefix(upid, utid)}_slice_${rawTrackIds}`;
      ctx.tracks.registerTrack({
        uri,
        title,
        tags: {
          trackIds,
          kind: ASYNC_SLICE_TRACK_KIND,
          scope: 'thread',
          utid,
          upid: upid ?? undefined,
        },
        chips: removeFalsyValues([
          isKernelThread === 0 && isMainThread === 1 && 'main thread',
        ]),
        track: new AsyncSliceTrack({trace: ctx, uri}, maxDepth, trackIds),
      });
      const track = new TrackNode({uri, title, sortOrder: 20});
      trackIds.forEach((id) =>
        trackMap.set(id, {trackNode: track, parentId, utid}),
      );
    }

    // Attach track nodes to parents / or the workspace if they have no parent
    trackMap.forEach((t) => {
      const parent = exists(t.parentId) && trackMap.get(t.parentId);
      if (parent !== false && parent !== undefined) {
        parent.trackNode.addChildInOrder(t.trackNode);
      } else {
        const group = getOrCreateGroupForThread(ctx.workspace, t.utid);
        group.addChildInOrder(t.trackNode);
      }
    });
  }

  async addUserAsyncSliceTracks(ctx: Trace): Promise<void> {
    const {engine} = ctx;
    const result = await engine.query(`
      with grouped_packages as materialized (
        select
          uid,
          group_concat(package_name, ',') as package_name,
          count() as cnt
        from package_list
        group by uid
      )
      select
        t.name as name,
        t.uid as uid,
        t.parent_id as parentId,
        t.track_ids as trackIds,
        __max_layout_depth(t.track_count, t.track_ids) as maxDepth,
        iif(g.cnt = 1, g.package_name, 'UID ' || g.uid) as packageName
      from _uid_track_track_summary_by_uid_and_name t
      left join grouped_packages g using (uid)
    `);

    const it = result.iter({
      name: STR_NULL,
      uid: NUM_NULL,
      packageName: STR_NULL,
      trackIds: STR,
      maxDepth: NUM,
      parentId: NUM_NULL,
    });

    const trackMap = new Map<
      number,
      {parentId: number | null; trackNode: TrackNode}
    >();

    for (; it.valid(); it.next()) {
      const {name, uid, maxDepth, parentId} = it;
      const kind = ASYNC_SLICE_TRACK_KIND;
      const userName = it.packageName === null ? `UID ${uid}` : it.packageName;
      const trackIds = it.trackIds.split(',').map((v) => Number(v));

      const title = getTrackName({
        name,
        uid,
        userName,
        kind,
        uidTrack: true,
      });

      const uri = `/async_slices_${name}_${uid}`;
      ctx.tracks.registerTrack({
        uri,
        title,
        tags: {
          trackIds: trackIds,
          kind: ASYNC_SLICE_TRACK_KIND,
        },
        track: new AsyncSliceTrack({trace: ctx, uri}, maxDepth, trackIds),
      });

      const track = new TrackNode({uri, title});
      trackIds.forEach((id) => trackMap.set(id, {trackNode: track, parentId}));
    }

    // Attach track nodes to parents / or the workspace if they have no parent
    trackMap.forEach((t) => {
      const parent = exists(t.parentId) && trackMap.get(t.parentId);
      if (parent !== false && parent !== undefined) {
        parent.trackNode.addChildInOrder(t.trackNode);
      } else {
        ctx.workspace.addChildInOrder(t.trackNode);
      }
    });
  }
}

export const plugin: PluginDescriptor = {
  pluginId: 'perfetto.AsyncSlices',
  plugin: AsyncSlicePlugin,
};
