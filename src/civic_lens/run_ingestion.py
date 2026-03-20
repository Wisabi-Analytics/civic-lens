from __future__ import annotations

import logging
from civic_lens.party_coding_loader import load_party_coding
from civic_lens.dcleapil_loader import load_dcleapil
from civic_lens.commons_2022_loader import load_commons_2022
from civic_lens.commons_2021_loader import load_commons_2021
from civic_lens.lookup_loader import load_all_lookups

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def main() -> None:
    logger.info('Phase 4 ingestion starting')
    load_party_coding()
    logger.info('Party coding lookup written')

    load_dcleapil()
    logger.info('DCLEAPIL interim file written')

    load_commons_2022()
    logger.info('Commons 2022 candidate and ward parquets written')

    load_commons_2021()
    logger.info('Commons 2021 completeness parquets written')

    load_all_lookups()
    logger.info('Lookup tables and IMD deciles written')

    logger.info('Phase 4 ingestion complete')


if __name__ == '__main__':
    main()
