// Copyright (C) 2023 The Android Open Source Project
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

import {v4 as uuidv4} from 'uuid';
import {GenericSliceDetailsTabConfig} from '../../frontend/generic_slice_details_tab';
import {BottomTabToSCSAdapter} from '../../public/utils';
import {Trace} from '../../public/trace';
import {PerfettoPlugin, PluginDescriptor} from '../../public/plugin';
import {PageLoadDetailsPanel} from './page_load_details_panel';
import {StartupDetailsPanel} from './startup_details_panel';
import {WebContentInteractionPanel} from './web_content_interaction_details_panel';
import {CriticalUserInteractionTrack} from './critical_user_interaction_track';
import {TrackNode} from '../../public/workspace';

class CriticalUserInteractionPlugin implements PerfettoPlugin {
  async onTraceLoad(ctx: Trace): Promise<void> {
    ctx.commands.registerCommand({
      id: 'perfetto.CriticalUserInteraction.AddInteractionTrack',
      name: 'Add track: Chrome interactions',
      callback: () => {
        const track = new TrackNode({
          uri: CriticalUserInteractionTrack.kind,
          title: 'Chrome Interactions',
        });
        ctx.workspace.addChildInOrder(track);
        track.pin();
      },
    });

    ctx.tracks.registerTrack({
      uri: CriticalUserInteractionTrack.kind,
      tags: {
        kind: CriticalUserInteractionTrack.kind,
      },
      title: 'Chrome Interactions',
      track: new CriticalUserInteractionTrack({
        trace: ctx,
        uri: CriticalUserInteractionTrack.kind,
      }),
    });

    ctx.tabs.registerDetailsPanel(
      new BottomTabToSCSAdapter({
        tabFactory: (selection) => {
          if (
            selection.kind === 'GENERIC_SLICE' &&
            selection.detailsPanelConfig.kind === PageLoadDetailsPanel.kind
          ) {
            const config = selection.detailsPanelConfig.config;
            return new PageLoadDetailsPanel({
              config: config as GenericSliceDetailsTabConfig,
              trace: ctx,
              uuid: uuidv4(),
            });
          }
          return undefined;
        },
      }),
    );

    ctx.tabs.registerDetailsPanel(
      new BottomTabToSCSAdapter({
        tabFactory: (selection) => {
          if (
            selection.kind === 'GENERIC_SLICE' &&
            selection.detailsPanelConfig.kind === StartupDetailsPanel.kind
          ) {
            const config = selection.detailsPanelConfig.config;
            return new StartupDetailsPanel({
              config: config as GenericSliceDetailsTabConfig,
              trace: ctx,
              uuid: uuidv4(),
            });
          }
          return undefined;
        },
      }),
    );

    ctx.tabs.registerDetailsPanel(
      new BottomTabToSCSAdapter({
        tabFactory: (selection) => {
          if (
            selection.kind === 'GENERIC_SLICE' &&
            selection.detailsPanelConfig.kind ===
              WebContentInteractionPanel.kind
          ) {
            const config = selection.detailsPanelConfig.config;
            return new WebContentInteractionPanel({
              config: config as GenericSliceDetailsTabConfig,
              trace: ctx,
              uuid: uuidv4(),
            });
          }
          return undefined;
        },
      }),
    );
  }
}

export const plugin: PluginDescriptor = {
  pluginId: 'perfetto.CriticalUserInteraction',
  plugin: CriticalUserInteractionPlugin,
};
