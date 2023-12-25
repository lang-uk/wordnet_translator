"""
Implementation of Bign translator for the wordnet
"""
from typing import Dict, List
from time import sleep
import html
from collections import Counter

from .abstract import AbstractSlidingWindowTranslator, AbstractDictionaryTranslator
from .bing_client import BingTranslatorClient
from .constants import ENGLISH, UKRAINIAN


class SlidingWindowBingTranslator(AbstractSlidingWindowTranslator):
    """
    The implementation of the wordnet translator using Bing translator API
    Redefines the parsing methods
    """

    def __init__(
        self,
        bing_apikey: str,
        group_by: int = 3,
        add_or: bool = True,
        add_quotes: bool = True,
        combine_in_one: bool = True,
        add_aux_words: bool = True,
        source_language=ENGLISH,
        target_language=UKRAINIAN,
    ) -> None:
        """
        Args:
            bing_apikey: bing api key
            **kwargs from the AbstractSlidingWindowTranslator
        Returns:
            None
        """
        self.bing_apikey: str = bing_apikey
        self.bing_translator: BingTranslatorClient = BingTranslatorClient(
            self.bing_apikey
        )

        super().__init__(
            group_by=group_by,
            add_or=add_or,
            add_quotes=add_quotes,
            combine_in_one=combine_in_one,
            add_aux_words=add_aux_words,
            source_language=source_language,
            target_language=target_language,
        )

    def estimate_tasks(self, tasks: List[Dict], price_per_mb: float = 10.0) -> float:
        return super().estimate_tasks(tasks, price_per_mb)

    def _unwrap_results(self, response: str) -> str:
        """
        Unwrap the results from the bing API
        Args:
            response: text response from the bing API
        Returns:
            Unescaped text
        """

        return html.unescape(response)

    def translate(self, task, sleep_between_samples=1):
        """
        Translate the task using bing translator
        """
        results = []
        sampled = self.generate_samples(task)
        for sample in sampled["samples"]:
            results.append(
                self.bing_translator.translate(
                    sample,
                    source_language=self.source_language,
                    target_language=self.target_language,
                )
            )
            sleep(sleep_between_samples)

        return self.parse_results(task, results)


class DictionaryBingTranslator(AbstractDictionaryTranslator):
    """
    A rather failed attempt to leverage dictionary service of the Bing API.
    Probably one day it's quality will be good enough to use it.
    """

    def __init__(
        self,
        bing_apikey: str,
        source_language=ENGLISH,
        target_language=UKRAINIAN,
    ):
        """
        Args:
            bing_apikey: bing api key
            **kwargs from the AbstractDictionaryTranslator
        """
        self.bing_apikey: str = bing_apikey
        self.bing_translator: BingTranslatorClient = BingTranslatorClient(
            self.bing_apikey
        )

        super().__init__(
            source_language=source_language,
            target_language=target_language,
        )

    #     [ "a", "n", "r", "s", "v" ]
    # a ADJ
    # r ADV
    # c CONJ
    # n NOUN
    # v VERB
    # x OTHER

    # DET
    # MODAL
    # PREP
    # PRON
    # Марьяна Романишин, [12 жовт. 2021 р., 09:18:00]:
    # Так, у цьому випадку adposition - це preposition. У різних мовах прийменники можуть
    # стояти перед іменником (preposition) або після іменника (postposition).
    # Термін adposition об'єднує одне і друге.
    # s також можна змапити на ADJ.

    def translate(self, task: Dict, sleep_between_samples: float = 1):
        """
        Pick the best translation from the dictionary
        """

        results = []
        sampled = self.generate_samples(task)
        for sample in sampled["samples"]:
            results.append(
                self.bing_translator.dictionary_lookup(
                    sample,
                    source_language=self.source_language,
                    target_language=self.target_language,
                )
            )
            sleep(sleep_between_samples)

        # TODO: align the types
        return self.parse_results(task=task, results=results)

    def parse_results(self, task: Dict, results: List[Dict]) -> Dict:
        """
        Parse the results of the translation
        Args:
            results: results to parse
        Returns:
            Dict with parsed results
        """
        terms: Counter = Counter()
        parsed_results: List[Dict] = []

        for r in results:
            if "normalizedTarget" in r:
                terms.update(r["normalizedTarget"])
            parsed_results.append(r)

        return {
            "raw": parsed_results,
            "terms": terms.most_common(),
            "definitions": [],
            "type": "dictionary",
        }

    def method_id(self):
        return f"{type(self).__name__}()"
