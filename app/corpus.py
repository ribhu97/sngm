"""Small versioned corpus: canonical accounts, bounded lookup, source snapshots."""
import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent/'content/corpus/diwali.v1.json').read_text())
SOURCES = {source['id']:source for source in DATA['sources']}
ACCOUNTS = {account['id']:account for account in DATA['accounts']}


def account_for(practice, query='', account_id=None):
    if account_id:
        if account_id not in ACCOUNTS or practice != 'diwali':
            raise ValueError('Account unavailable for this Current.')
        selected = ACCOUNTS[account_id]
    elif practice != 'diwali':
        return dict(id=f'{practice}.unknown.v1',version=1,kind='unknown',title='A family-specific Unknown',
                    text='This demo has no sourced account for this practice yet. Your family’s meaning remains a question to explore, not something to infer.',citations=[])
    else:
        q = query.casefold()
        if any(word in q for word in ['shakt','bhakt','tantra']):
            key = 'shakti-bhakti'
        elif ('kali' in q and any(word in q for word in ['lakshmi','laxmi'])) or any(word in q for word in ['versus','difference','compare','both']):
            key = 'comparison'
        elif any(word in q for word in ['lakshmi','laxmi','sri sukta','wealth','prosperity']):
            key = 'lakshmi'
        elif any(word in q for word in ['kali','shyama','bengal']):
            key = 'kali'
        elif any(word in q for word in ['offering','flower','fruit','water','gita']):
            key = 'offering'
        else:
            key = 'overview'
        selected = ACCOUNTS[f'diwali.{key}.v1']
    result = deepcopy(selected)
    result.update(version=DATA['version'],kind='cited',status=DATA['status'],
                  presentation_note=DATA['editorial_note'],citations=[deepcopy(SOURCES[key]) for key in selected['source_ids']])
    return result
