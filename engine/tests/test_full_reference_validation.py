import copy
import unittest

from scripts.sync_internal_research_cache import SyncError, _validate_bundle, sync


class FullReferenceValidationTests(unittest.TestCase):
    def setUp(self):
        tickers = [f'{chr(65+i//100)}{i%100:02d}' for i in range(405)]
        self.bundle = dict(exchange='HOSE', data_role='INTERNAL_RESEARCH', universe_count=405,
            public_release_allowed=False, public_action_allowed=False, catalyst_alpha_weight_allowed=False,
            institutional_alpha_weight_allowed=False, internal_research_ready_count=0,
            tickers={t:dict(ticker=t,release=dict(public_action_allowed=False,internal_research_ready=False)) for t in tickers})

    def test_zero_research_is_valid_reference_but_never_promoted(self):
        self.assertEqual(_validate_bundle(self.bundle,full_reference=True),{})
        with self.assertRaises(SyncError):
            _validate_bundle(self.bundle)  # Legacy research-only import remains strict.

    def test_incomplete_or_overclaimed_reference_cannot_pass(self):
        for kind in ('partial','identity','public','alpha','grade','missing_grade'):
            b=copy.deepcopy(self.bundle);first=next(iter(b['tickers']))
            if kind=='partial': b['tickers'].pop(first);b['universe_count']=404
            if kind=='identity': b['tickers'][first]['ticker']='ZZZ'
            if kind=='public': b['public_action_allowed']=True
            if kind=='alpha': b['catalyst_alpha_weight_allowed']=True
            if kind=='grade': b['internal_research_ready_count']=1
            if kind=='missing_grade': b['tickers'][first]['release'].pop('internal_research_ready')
            with self.subTest(kind=kind),self.assertRaises(SyncError):
                _validate_bundle(b,full_reference=True)

    def test_reference_validation_cannot_use_legacy_writer(self):
        with self.assertRaisesRegex(SyncError,'dry-run only'):
            sync(None,full_reference=True)
