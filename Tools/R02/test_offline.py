"""Offline mathematical and data-integrity checks. These do not compile HLSL."""
import importlib.util
import ast
import json
import math
import random
import tempfile
import unittest
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMP_ROOT = HERE.parents[1] / 'tmp/R02-tests'
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def temporary_directory():
    return tempfile.TemporaryDirectory(prefix='case-', dir=TEMP_ROOT)

spec = importlib.util.spec_from_file_location('r02_summary', HERE / 'summarize.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class RippleSupportTests(unittest.TestCase):
    def test_old_lifetime_exceeds_history_at_high_rate(self):
        old_lifetime, rate = 0.9, 3.0
        age_of_removed_event = 2.0 / rate
        self.assertLess(age_of_removed_event, old_lifetime)
        self.assertGreater(1.0-age_of_removed_event/old_lifetime, 0.25)

    def test_candidate_lifetime_fits_two_periods(self):
        rng = random.Random(20261023)
        for _ in range(20000):
            rate = rng.uniform(0.2, 3)
            scatter, a, b = (rng.random() for _ in range(3))
            lifetime = min((0.65+a*0.25)*(1-scatter)+(0.48+b*0.42)*scatter, 1.95/rate)
            self.assertGreater(lifetime, 0)
            self.assertLess(lifetime*rate, 2)

    def test_spatial_support_and_early_exit_bound(self):
        # Maximum radius=.48*1.25=.6 cells; centers stay in [.02,.98].
        # A center two cells away is >=1.02 cells away, so no ring crest is lost.
        # Gaussian tails are not compact support: this does not prove exact zero outside.
        self.assertLess(0.48*1.25, 1.02)
        rng = random.Random(17)
        for _ in range(10000):
            radius_max = rng.uniform(1, 100)
            scatter, variation = rng.random(), rng.random()
            radius = radius_max*((1-scatter)+scatter*(0.6+variation*0.65))
            self.assertLessEqual(radius, radius_max*1.25)

    def test_slope_normal_is_finite_and_upward(self):
        for sx in (-1e10, -0.18, 0, 0.18, 1e10):
            for sy in (-1e10, -0.18, 0, 0.18, 1e10):
                x, y = max(-0.18, min(0.18, sx)), max(-0.18, min(0.18, sy))
                z = 1/math.sqrt(x*x+y*y+1)
                self.assertTrue(math.isfinite(z))
                self.assertGreater(z, 0.96)

    def test_capture_matrix_has_required_endpoints(self):
        cfg = json.loads((HERE / 'acceptance.json').read_text())
        self.assertEqual(len({s['name'] for s in cfg['states']}), len(cfg['states']))
        for key, endpoints in {'RippleSizeScale': (0.25, 2), 'RippleDensityScale': (0, 2),
                               'RippleSpeedScale': (0.1, 2), 'RippleStrengthScale': (0, 3),
                               'RippleRandomness': (0, 1)}.items():
            values = {s[key] for s in cfg['states'] if key in s}
            self.assertTrue(set(endpoints).issubset(values), key)


class SummaryIntegrityTests(unittest.TestCase):
    def test_duplicate_columns_are_checked_for_measured_fields(self):
        with temporary_directory() as directory:
            path = Path(directory) / 'duplicates.csv'
            path.write_text('FrameTime,GPUTime,ShadowCacheUsageMB,ShadowCacheUsageMB\n20,18,1,2\n')
            self.assertEqual(summary.read_csv(path)['GPUTime']['median_ms'], 18)
            path.write_text('FrameTime,GPUTime,GPUTime\n20,18,19\n')
            with self.assertRaises(ValueError):
                summary.read_csv(path)

    def test_filters_metadata_and_nonfinite_values(self):
        with temporary_directory() as directory:
            path = Path(directory) / 'sample.csv'
            path.write_text('FrameTime,GPUTime\n16,10\n18,12\nmetadata,text\nnan,99\n20,inf\n', encoding='utf-8')
            result = summary.read_csv(path)
            self.assertEqual(result['GPUTime']['count'], 2)
            self.assertEqual(result['GPUTime']['median_ms'], 11)
            self.assertEqual(result['FrameTime']['count'], 3)

    def test_rejects_zero_gpu_data(self):
        with temporary_directory() as directory:
            folder = Path(directory)
            entries = []
            for i, variant in enumerate(['off','on','on','off','on','off','off','on']):
                name = '%s.csv' % i
                (folder / name).write_text('FrameTime,GPUTime,DrawCall/Basepass\n'+'16,0,100\n'*120)
                entries.append({'variant': variant, 'csv_requested': name})
            (folder / 'result.json').write_text(json.dumps({'mode': 'benchmark','status':'completed','samples':entries}))
            with self.assertRaisesRegex(ValueError, 'GPUTime'):
                summary.summarize(folder)

    def test_abba_pairing(self):
        with temporary_directory() as directory:
            folder = Path(directory)
            entries = []
            for i, variant in enumerate(['off','on','on','off','on','off','off','on']):
                name = '%s.csv' % i
                gpu = 11 if variant == 'on' else 10
                (folder / name).write_text('FrameTime,GPUTime,DrawCall/Basepass\n'+('16,%s,100\n' % gpu)*120)
                entries.append({'variant': variant, 'csv_requested': name})
            (folder / 'result.json').write_text(json.dumps({'mode':'benchmark','status':'completed','samples':entries}))
            result = summary.summarize(folder)
            self.assertEqual(result['paired_gpu_median_deltas_ms'], [1,1,1,1])
            self.assertEqual(result['median_paired_gpu_delta_ms'], 1)

    def test_rejects_ui_only_gpu_samples(self):
        with temporary_directory() as directory:
            folder = Path(directory)
            entries = []
            for i, variant in enumerate(['off','on','on','off','on','off','off','on']):
                name = '%s.csv' % i
                (folder / name).write_text('FrameTime,GPUTime,DrawCall/Basepass\n'+'16,2,0\n'*120)
                entries.append({'variant': variant, 'csv_requested': name})
            (folder / 'result.json').write_text(json.dumps({'mode':'benchmark','status':'completed','samples':entries}))
            with self.assertRaisesRegex(ValueError, 'scene-rendered'):
                summary.summarize(folder)

    def test_rejects_incomplete_batch(self):
        with temporary_directory() as directory:
            folder = Path(directory)
            (folder / 'result.json').write_text(json.dumps({'mode':'benchmark','status':'completed','samples':[]}))
            with self.assertRaisesRegex(ValueError, 'ABBA'):
                summary.summarize(folder)


class CallbackTests(unittest.TestCase):
    def test_rotations_use_explicit_axes(self):
        tree = ast.parse((HERE / 'ue_acceptance.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                 isinstance(n.func, ast.Attribute) and n.func.attr == 'Rotator']
        self.assertTrue(calls)
        for call in calls:
            self.assertFalse(call.args)
            self.assertEqual({k.arg for k in call.keywords}, {'pitch','yaw','roll'})

    def context(self):
        tree = ast.parse((HERE / 'ue_acceptance.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'tick')
        context = {'TICK_ACTIVE': False, 'MODE': 'capture', 'time': time, 'START': time.monotonic(),
                   'STATE': {'errors': []}, 'traceback': traceback, 'finished': []}
        context['finish'] = lambda success: context['finished'].append(success)
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'worker-tick', 'exec'), context)
        return context

    def test_busy_tick_does_not_advance_generator(self):
        context = self.context()
        context['TICK_ACTIVE'] = True
        context['tick'](0)
        self.assertEqual(context['STATE']['errors'], [])
        self.assertEqual(context['finished'], [])

    def test_nested_slate_callback_is_ignored(self):
        context = self.context()
        def task():
            context['tick'](0)
            yield
        context['TASKS'] = task()
        context['tick'](0)
        self.assertFalse(context['TICK_ACTIVE'])
        self.assertEqual(context['STATE']['errors'], [])
        context['tick'](0)
        self.assertEqual(context['finished'], [True])


if __name__ == '__main__':
    unittest.main(verbosity=2)
