#!/usr/env python
# -*- coding: utf-8 -*-
__author__ = 'eduardo'

import logging
import time
import json
import operator
from lbsociam.model.crimes import CrimesBase
from lbsociam.model.lbstatus import StatusBase
from lbsociam.model.dictionary import DictionaryBase
from lbsociam.lib import lda
from requests.exceptions import HTTPError
from pyramid.response import Response
from ..lib import utils

log = logging.getLogger()


class AnalysisController(object):
    """
    Abalysis controller page
    """
    def __init__(self, request):
        """
        View constructor for analysis
        :param request: Pyramid request
        """
        self.request = request
        self.crimes_base = CrimesBase()
        self.status_base = StatusBase()
        self.dic_base = DictionaryBase()

    def crime_analysis(self):
        """
        View to load crime data
        :return:
        """
        search_url = self.status_base.lbgenerator_rest_url + self.status_base.lbbase.metadata.name + '/doc'
        terms = self.dic_base.get_token_frequency(limit=20)

        return {
            'search_url': search_url,
            'key': self.status_base.gmaps_api_key,
            'terms': terms
        }

    def crime_topics(self):
        """
        Generate crime topics
        :return: dict with term frequency calculated by LDA
        """
        n_topics = self.request.params.get('n_topics')
        if n_topics is None:
            # TODO: Get this value from crimes taxonomy base
            n_topics = 4
        else:
            n_topics = int(n_topics)

        saida = lda.crime_topics(
            status_base=self.status_base,
            crimes_base=self.crimes_base,
            n_topics=n_topics
        )

        return saida

    def crime_locations(self):
        """
        Get crimes with locations included
        """

        status_locations = self.status_base.get_locations()

        # Now find category
        i = 0
        for status in status_locations['results']:
            if status.get('events_tokens'):
                category = utils.get_category(status['events_tokens'])
            else:
                category = utils.get_category([status['search_term']])

            # Update dict with recently found category
            if category is None:
                log.error("Category not found for status %s\nSearch term: %s",
                          status['_metadata']['id_doc'], status['search_term'])

            status_locations['results'][i]['category'] = category

            # JSON to dict in source
            status_locations['results'][i]['source'] = json.loads(status['source'])

            i += 1

        return {
            'status': status_locations
        }

    def crime_hashtags(self):
        """
        Generate hashtag clouds
        """
        # Number of elements to be in hashtags by default
        n = self.request.params.get('n')
        if n is None:
            n = 50
        else:
            n = int(n)

        log.debug("HASHTAGS: processing starting at %s", time.ctime())
        status = self.status_base.get_hashtags()
        hashtags = dict()
        for elm in status['results']:
            if elm is not None:
                for elm_hashtag in elm['hashtags']:
                    # Calculate hashtag frequency
                    if hashtags.get(elm_hashtag) is not None:
                        hashtags[elm_hashtag] += 1
                    else:
                        hashtags[elm_hashtag] = 1

        # Ordering results and selecting first 20
        sorted_tags = dict(sorted(hashtags.items(), key=lambda x: x[1], reverse=True)[:n])

        log.debug("HASHTAGS: processing over at %s", time.ctime())

        return {'hashtags': sorted_tags}