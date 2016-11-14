from __future__ import unicode_literals
from datetime import date
from itertools import groupby
import re

import transaction
from nameparser import HumanName
from sqlalchemy.orm import joinedload_all, joinedload
from clldutils.misc import slug
from clld.util import LGR_ABBRS
from clld.scripts.util import Data, initializedb
from clld.db.meta import DBSession
from clld.db.models import common
from clld_glottologfamily_plugin.util import load_families
from pyconcepticon.api import Concepticon

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word, Variety
from dictionaria.lib.submission import REPOS, Submission


def main(args):
    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=date(2015, 10, 1),
        contact='dictionaria@eva.mpg.de',
        domain='dictionaria.clld.org',
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    ed = data.add(
        common.Contributor, 'hartmanniren', id='hartmanniren', name='Iren Hartmann')
    common.Editor(dataset=dataset, contributor=ed)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}
    comparison_meanings_alt_labels = {}

    print('loading concepts ...')

    concepticon = Concepticon(
        REPOS.joinpath('..', '..', 'concepticon', 'concepticon-data'))
    if not args.no_concepts:
        for conceptset in concepticon.conceptsets.values():
            cm = data.add(
                ComparisonMeaning,
                conceptset.id,
                id=conceptset.id,
                name=conceptset.gloss.lower(),
                description=conceptset.definition,
                concepticon_url='http://concepticon.clld.org/parameters/%s' % conceptset.id)
            comparison_meanings[cm.name] = cm
        for conceptlist in concepticon.conceptlists.values():
            for concept in conceptlist.concepts.values():
                if concept.concepticon_id:
                    comparison_meanings_alt_labels.setdefault(
                        concept.label.lower(),
                        data['ComparisonMeaning'][concept.concepticon_id])

    DBSession.flush()

    print('... done')

    comparison_meanings = {k: v.pk for k, v in comparison_meanings.items()}
    comparison_meanings_alt_labels = {
        k: v.pk for k, v in comparison_meanings_alt_labels.items()}

    submissions = []

    for submission in REPOS.joinpath(
            'submissions-internal' if args.internal else 'submissions').glob('*'):
        if not submission.is_dir():
            continue

        try:
            submission = Submission(submission)
        except ValueError:
            continue

        md = submission.md
        if md is None:
            continue

        id_ = submission.id
        if args.dict and args.dict != id_ and args.dict != 'all':
            continue
        lmd = md['language']
        props = md.get('properties', {})

        language = data['Variety'].get(lmd['glottocode'])
        if not language:
            language = data.add(
                Variety, lmd['glottocode'], id=lmd['glottocode'], name=lmd['name'])

        md['date_published'] = md['date_published'] or date.today().isoformat()
        if '-' not in md['date_published']:
            md['date_published'] = md['date_published'] + '-01-01'
        dictionary = data.add(
            Dictionary,
            id_,
            id=id_,
            name=props.get('title', lmd['name'] + ' Dictionary'),
            description=submission.description,
            language=language,
            published=date(*map(int, md['date_published'].split('-'))),
            jsondata=dict(custom_fields=props.get('custom_fields', [])))

        for i, cname in enumerate(md['authors']):
            name = HumanName(cname)
            cid = slug('%s%s' % (name.last, name.first))
            contrib = data['Contributor'].get(cid)
            if not contrib:
                contrib = data.add(common.Contributor, cid, id=cid, name=cname)
            DBSession.add(common.ContributionContributor(
                ord=i + 1,
                primary=True,
                contributor=contrib,
                contribution=dictionary))

        submissions.append((dictionary.id, language.id, submission))
    transaction.commit()

    for did, lid, submission in submissions:
        transaction.begin()
        print('loading %s ...' % submission.id)
        dictdata = Data()
        lang = Variety.get(lid)
        submission.load_examples(dictdata, lang)
        submission.dictionary.load(
            submission,
            dictdata,
            Dictionary.get(did),
            lang,
            comparison_meanings,
            comparison_meanings_alt_labels,
            submission.md.get('properties', {}).get('labels', {}))
        transaction.commit()
        print('... done')

    transaction.begin()
    load_families(
        Data(),
        [v for v in DBSession.query(Variety) if re.match('[a-z]{4}[0-9]{4}', v.id)])


def prime_cache(cfg):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    for meaning in DBSession.query(ComparisonMeaning).options(
        joinedload_all(common.Parameter.valuesets, common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])
        if meaning.representation == 0:
            meaning.active = False

    q = DBSession.query(Word)\
        .order_by(common.Unit.language_pk, common.Unit.name, common.Unit.pk)\
        .options(joinedload(Word.meanings))
    for _, words in groupby(q, lambda u: u.name):
        words = list(words)
        for i, word in enumerate(words):
            word.description = ' / '.join(m.name for m in word.meanings if m.language == 'en')
            word.number = i + 1 if len(words) > 1 else 0
            DBSession.add(common.Unit_data(
                object_pk=word.pk,
                key='Semantic domain',
                value=' / '.join(m.semantic_domain for m in word.meanings if m.semantic_domain)))

    for d in DBSession.query(Dictionary).options(joinedload(Dictionary.words)):
        d.count_words = len(d.words)


if __name__ == '__main__':
    initializedb(
        (("--internal",), dict(action='store_true')),
        (("--no-concepts",), dict(action='store_true')),
        (("--dict",), dict()),
        create=main, prime_cache=prime_cache)
