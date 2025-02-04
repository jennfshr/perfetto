#!/usr/bin/env python3
# Copyright (C) 2024 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License a
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from python.generators.diff_tests.testing import Csv, DataPath, TextProto
from python.generators.diff_tests.testing import DiffTestBlueprint
from python.generators.diff_tests.testing import TestSuite


class LinuxCpu(TestSuite):

  def test_cpu_utilization_per_second(self):
    return DiffTestBlueprint(
        trace=DataPath('example_android_trace_30s.pb'),
        query="""
        INCLUDE PERFETTO MODULE linux.cpu.utilization.system;

        SELECT * FROM cpu_utilization_per_second;
        """,
        out=Csv("""
        "ts","utilization","unnormalized_utilization"
        70000000000,0.004545,0.036362
        71000000000,0.022596,0.180764
        72000000000,0.163393,1.307146
        73000000000,0.452122,3.616972
        74000000000,0.525557,4.204453
        75000000000,0.388632,3.109057
        76000000000,0.425447,3.403579
        77000000000,0.201112,1.608896
        78000000000,0.280247,2.241977
        79000000000,0.345228,2.761827
        80000000000,0.303258,2.426064
        81000000000,0.487522,3.900172
        82000000000,0.080542,0.644336
        83000000000,0.362450,2.899601
        84000000000,0.076438,0.611501
        85000000000,0.110689,0.885514
        86000000000,0.681488,5.451901
        87000000000,0.808331,6.466652
        88000000000,0.941768,7.534142
        89000000000,0.480556,3.844446
        90000000000,0.453268,3.626142
        91000000000,0.280310,2.242478
        92000000000,0.006381,0.051049
        93000000000,0.030991,0.247932
        94000000000,0.031981,0.255845
        95000000000,0.027931,0.223446
        96000000000,0.063066,0.504529
        97000000000,0.023847,0.190773
        98000000000,0.011291,0.090328
        99000000000,0.024065,0.192518
        100000000000,0.001964,0.015711
        """))

  def test_cpu_process_utilization_per_second(self):
    return DiffTestBlueprint(
        trace=DataPath('example_android_trace_30s.pb'),
        query="""
        INCLUDE PERFETTO MODULE linux.cpu.utilization.process;

        SELECT *
        FROM cpu_process_utilization_per_second(10);
        """,
        out=Csv("""
        "ts","utilization","unnormalized_utilization"
        72000000000,0.000187,0.001495
        73000000000,0.000182,0.001460
        77000000000,0.000072,0.000579
        78000000000,0.000275,0.002204
        82000000000,0.000300,0.002404
        83000000000,0.000004,0.000034
        87000000000,0.000133,0.001065
        88000000000,0.000052,0.000416
        89000000000,0.000212,0.001697
        92000000000,0.000207,0.001658
        97000000000,0.000353,0.002823
        """))

  def test_cpu_thread_utilization_per_second(self):
    return DiffTestBlueprint(
        trace=DataPath('example_android_trace_30s.pb'),
        query="""
        INCLUDE PERFETTO MODULE linux.cpu.utilization.thread;

        SELECT *
        FROM cpu_thread_utilization_per_second(10);
        """,
        out=Csv("""
        "ts","utilization","unnormalized_utilization"
        70000000000,0.000024,0.000195
        72000000000,0.000025,0.000200
        73000000000,0.000053,0.000420
        74000000000,0.000044,0.000352
        75000000000,0.000058,0.000461
        76000000000,0.000075,0.000603
        77000000000,0.000051,0.000407
        78000000000,0.000047,0.000374
        79000000000,0.000049,0.000396
        80000000000,0.000084,0.000673
        81000000000,0.000041,0.000329
        82000000000,0.000048,0.000383
        83000000000,0.000040,0.000323
        84000000000,0.000018,0.000145
        85000000000,0.000053,0.000421
        86000000000,0.000121,0.000972
        87000000000,0.000049,0.000392
        88000000000,0.000036,0.000285
        89000000000,0.000033,0.000266
        90000000000,0.000050,0.000401
        91000000000,0.000025,0.000201
        92000000000,0.000009,0.000071
        """))

  def test_cpu_cycles(self):
    return DiffTestBlueprint(
        trace=DataPath('android_postboot_unlock.pftrace'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.system;

             SELECT
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles;
             """),
        out=Csv("""
        "millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
        36093928491870,36093,17131594098,500000,2850000,2112132
            """))

  def test_cpu_cycles_in_interval(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.system;

             SELECT
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles_in_interval(TRACE_START(), TRACE_DUR() / 10);
             """),
        out=Csv("""
          "millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
          5839969682564,5839,9476034254,614400,1708800,617686
            """))

  def test_cpu_cycles_per_cpu(self):
    return DiffTestBlueprint(
        trace=DataPath('android_postboot_unlock.pftrace'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.system;

             SELECT
              cpu,
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles_per_cpu;
             """),
        out=Csv("""
          "cpu","millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
          0,4007488375822,4007,2260291804,930000,1803000,1775516
          1,3985923237512,3985,2247149674,930000,1803000,1776869
          2,4047926756581,4047,2276274170,930000,1803000,1781496
          3,3992276081242,3992,2248956757,930000,1803000,1778975
          4,5134318459625,5134,2203887266,553000,2348000,2335531
          5,5615703220380,5615,2438499077,553000,2348000,2308698
          6,4715590442538,4715,1737264802,500000,2850000,2725191
          7,4594701918170,4594,1719270548,500000,2850000,2685290
            """))

  def test_cpu_cycles_per_cpu_in_interval(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.system;

             SELECT
              cpu,
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles_per_cpu_in_interval(TRACE_START(), TRACE_DUR() / 10);
             """),
        out=Csv("""
          "cpu","millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
          0,5762458673747,5762,9350177660,614400,1708800,617691
          1,72344785675,72,117748675,614400,614400,615831
          2,533252160,0,617190,864000,864000,871327
          3,4632970982,4,7490729,614400,864000,620044
            """))

  def test_cpu_cycles_per_thread(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.thread;

             SELECT
               AVG(millicycles) AS millicycles,
               AVG(megacycles) AS megacycles,
               AVG(runtime) AS runtime,
               AVG(min_freq) AS min_freq,
               AVG(max_freq) AS max_freq,
               AVG(avg_freq) AS avg_freq
             FROM cpu_cycles_per_thread;
             """),
        out=Csv("""
            "millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
            25048302164.445362,24.624742,16080173.697531,1402708.453608,1648468.453608,1582627.707216
            """))

  def test_cpu_cycles_per_thread_in_interval(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.thread;

             SELECT
              utid,
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles_per_thread_in_interval(TRACE_START(), TRACE_DUR() / 10)
             WHERE utid < 100
             """),
        out=Csv("""
            "utid","millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
            1,48593411952,48,79090840,614400,614400,615792
            14,613205232254,613,998055394,614400,614400,615792
            15,527593574058,527,858713502,614400,614400,615793
            16,291560471712,291,474545040,614400,614400,615792
            30,2893791427,2,4709947,614400,614400,615831
            61,72890117928,72,118636260,614400,614400,615792
            62,282929432,0,165572,1708800,1708800,1714723
            92,1071631296,1,1240314,864000,864000,867015
            """))

  def test_cpu_cycles_per_process(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.process;

             SELECT
               AVG(millicycles) AS millicycles,
               AVG(megacycles) AS megacycles,
               AVG(runtime) AS runtime,
               AVG(min_freq) AS min_freq,
               AVG(max_freq) AS max_freq,
               AVG(avg_freq) AS avg_freq
             FROM cpu_cycles_per_process;
             """),
        out=Csv("""
            "millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
            83434563989.406891,82.979310,53248030.726027,1193710.344828,1683773.793103,1536705.400000
            """))

  def test_cpu_cycles_per_process_in_interval(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.utilization.process;

             SELECT
              upid,
              millicycles,
              megacycles,
              runtime,
              min_freq,
              max_freq,
              avg_freq
             FROM cpu_cycles_per_process_in_interval(TRACE_START(), TRACE_DUR() / 10)
             WHERE upid < 30;
             """),
        out=Csv("""
          "upid","millicycles","megacycles","runtime","min_freq","max_freq","avg_freq"
          1,121483529880,121,197727100,614400,614400,615792
          14,613205232254,613,998055394,614400,614400,615792
          15,527593574058,527,858713502,614400,614400,615793
          16,291560471712,291,474545040,614400,614400,615792
            """))

  # Test CPU frequency counter grouping.
  def test_cpu_eos_counters_freq(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.frequency;
             select
               track_id,
               freq,
               cpu,
               sum(dur) as dur
             from cpu_frequency_counters
             GROUP BY freq, cpu
             """),
        out=Csv("""
            "track_id","freq","cpu","dur"
            33,614400,0,4755967239
            34,614400,1,4755971561
            35,614400,2,4755968228
            36,614400,3,4755964320
            33,864000,0,442371195
            34,864000,1,442397134
            35,864000,2,442417916
            36,864000,3,442434530
            33,1363200,0,897122398
            34,1363200,1,897144167
            35,1363200,2,897180154
            36,1363200,3,897216772
            33,1708800,0,2553979530
            34,1708800,1,2553923073
            35,1708800,2,2553866772
            36,1708800,3,2553814688
            """))

  # Test CPU idle state counter grouping.
  def test_cpu_eos_counters_idle(self):
    return DiffTestBlueprint(
        trace=DataPath('android_cpu_eos.pb'),
        query=("""
             INCLUDE PERFETTO MODULE linux.cpu.idle;
             select
               track_id,
               idle,
               cpu,
               sum(dur) as dur
             from cpu_idle_counters
             GROUP BY idle, cpu
             """),
        out=Csv("""
             "track_id","idle","cpu","dur"
             0,-1,0,2839828332
             37,-1,1,1977033843
             32,-1,2,1800498713
             1,-1,3,1884366297
             0,0,0,1833971336
             37,0,1,2285260950
             32,0,2,1348416182
             1,0,3,1338508968
             0,1,0,4013820433
             37,1,1,4386917600
             32,1,2,5532102915
             1,1,3,5462026920
            """))

  def test_linux_cpu_idle_stats(self):
    return DiffTestBlueprint(
        trace=TextProto(r"""
          packet {
            ftrace_events {
              cpu: 0
              event: {
                timestamp: 200000000000
                pid: 2
                cpu_frequency: {
                  state : 1704000
                  cpu_id: 0
                }
              }
              event: {
                timestamp: 200000000000
                pid: 2
                cpu_idle: {
                  state: 4294967295
                  cpu_id: 0
                }
              }
              event {
                timestamp: 200001000000
                pid: 2
                cpu_idle: {
                  state : 1
                  cpu_id: 0
                }
              }
              event: {
                timestamp: 200002000000
                pid  : 2
                cpu_idle: {
                  state : 4294967295
                  cpu_id: 0
                }
              }
              event {
                timestamp: 200003000000
                pid: 2
                cpu_idle: {
                  state : 1
                  cpu_id: 0
                }
              }
              event: {
                timestamp: 200004000000
                pid: 2
                cpu_idle: {
                  state : 4294967295
                  cpu_id: 0
                }
              }
              event: {
                timestamp: 200005000000
                pid: 2
                cpu_frequency: {
                  state: 300000
                  cpu_id: 0
                }
              }
            }
            trusted_uid: 9999
            trusted_packet_sequence_id: 2
          }
         """),
        query="""
         INCLUDE PERFETTO MODULE linux.cpu.idle_stats;
         SELECT * FROM cpu_idle_stats;
         """,
        out=Csv("""
         "cpu","state","count","dur","avg_dur","idle_percent"
         0,2,2,2000000,1000000,40.000000
         """))

  def test_linux_cpu_idle_time_in_state(self):
    return DiffTestBlueprint(
        trace=TextProto(r"""
        packet {
          sys_stats {
            cpuidle_state {
              cpu_id: 0
              cpuidle_state_entry {
                state: "C8"
                duration_us: 1000000
              }
            }
          }
          timestamp: 200000000000
          trusted_packet_sequence_id: 2
        }
        packet {
          sys_stats {
            cpuidle_state {
              cpu_id: 0
              cpuidle_state_entry {
                state: "C8"
                duration_us: 1000100
              }
            }
          }
          timestamp: 200001000000
          trusted_packet_sequence_id: 2
        }
        packet {
          sys_stats {
            cpuidle_state {
              cpu_id: 0
              cpuidle_state_entry {
                state: "C8"
                duration_us: 1000200
              }
            }
          }
          timestamp: 200002000000
          trusted_packet_sequence_id: 2
        }
         """),
        query="""
         INCLUDE PERFETTO MODULE linux.cpu.idle_time_in_state;
         SELECT * FROM cpu_idle_time_in_state_counters;
         """,
        out=Csv("""
         "ts","state_name","idle_percentage","total_residency","time_slice"
          200001000000,"cpuidle.C8",10.000000,100.000000,1000
          200002000000,"cpuidle.C8",10.000000,100.000000,1000
          200001000000,"cpuidle.C0",90.000000,900.000000,1000
          200002000000,"cpuidle.C0",90.000000,900.000000,1000
         """))
