"""
Abstract classes for translators
"""

from typing import Dict, Union, Tuple, List, Any
import logging
import re
from collections import Counter

from .constants import ENGLISH, UKRAINIAN
from .utils import sliding_window


logger = logging.getLogger("wordnet_translator")


class AbstractTranslator:
    """
    Abstract class for translators (api or model based)
    """

    def __init__(
        self, source_language: str = ENGLISH, target_language: str = UKRAINIAN
    ) -> None:
        """
        Initialize translator
        Args:
            source_language: source language
            target_language: target language
        Returns:

        """
        self.source_language = source_language
        self.target_language = target_language

    def generate_samples(self, task):
        """
        Generate samples for the task
        Args:
            task: task todo
        Returns:
            todo
        """
        raise NotImplementedError()

    def translate(self, task: Dict, sleep_between_samples: float = 1):
        """
        Translate the task using external service or a local model
        Args:
            task: sysnet task to translate
            sleep_between_samples: sleep between samples
        Returns:
            todo
        """
        raise NotImplementedError()

    def parse_results(self, task: Dict, results: List[Dict]):
        """
        Parse the results of the translation
        Args:
            task: original synset task
            results: results to parse
        Returns:
            todo
        """
        raise NotImplementedError()

    def method_id(self) -> str:
        """
        Return method id (which uniquely identifies the initialized translator)
        """
        raise NotImplementedError()


class AbstractSlidingWindowTranslator(AbstractTranslator):
    """
    Abstract class for translators that use sliding window to combine lemmas
    of the same synset
    """

    def __init__(
        self,
        group_by: int = 3,
        add_or: bool = True,
        add_quotes: bool = True,
        combine_in_one: bool = True,
        add_aux_words: bool = True,
        source_language: str = ENGLISH,
        target_language: str = UKRAINIAN,
    ) -> None:
        """
        Initialize translator
        Args:
            group_by: number of lemmas in window to combine
            add_or: add 'or' between last two lemmas
            add_quotes: add quotes around lemmas
            combine_in_one: combine all samples in one todo
            add_aux_words: add auxiliary words (e.g. 'the' for nouns, 'to' for verbs)
            source_language: source language
            target_language: target language
        Returns:
            None
        """
        super().__init__(
            source_language=source_language, target_language=target_language
        )

        self.group_by = group_by
        self.add_or = add_or
        self.add_quotes = add_quotes
        self.combine_in_one = combine_in_one
        self.add_aux_words = add_aux_words

    def _unwrap_results(self, response: Any) -> str:
        """
        Unwrap the text of response from the translator into a structured form
        """
        raise NotImplementedError()

    def method_id(self) -> str:
        return (
            f"{type(self).__name__}(group_by={self.group_by},add_or={self.add_or},"
            + f"add_quotes={self.add_quotes},combine_in_one={self.combine_in_one},"
            + f"add_aux_words={self.add_aux_words})"
        )

    def generate_samples(self, task: Dict) -> Dict:
        """
        Generates the list of sentences to translate given the wordnet synset according to
        the class parameters. For example, grouping different lemmas into the chunks
        to provide more context for the translator.

        Args:
            task: wordnet synset task to generate samples for
        Returns:
            dict with the list of samples and the total number of lemmas
        """
        samples = []
        total_samples = 0
        words = list(task["words"].values())

        if self.add_aux_words:
            if task["pos"] == "v":
                words = [f"to {w}" for w in words]
            elif task["pos"] == "n":
                words = [f"the {w}" for w in words]

        if self.add_quotes:
            words = [f'"{w}"' for w in words]

        chunks: List[Union[Tuple, List]] = []

        if len(words) < self.group_by:
            chunks = [words]
        else:
            chunks = list(sliding_window(words, self.group_by))

        for chunk in chunks:
            total_samples += len(chunk)

            if self.add_or and len(chunk) > 1:
                lemmas = ", ".join(chunk[:-1]) + f" or {chunk[-1]}"
            else:
                lemmas = ", ".join(chunk)

            if task["definition"]:
                samples.append(f"{lemmas}: {task['definition'][0]}")
            else:
                samples.append(lemmas)

        if self.combine_in_one:
            return {
                "samples": ["<br/>\n\n".join(samples)],
                "total_lemmas": total_samples,
            }
        else:
            return {"samples": samples, "total_lemmas": total_samples}

    def estimate_tasks(
        self, tasks: List[Dict], price_per_mb: float = 1.0 / 1024 / 1024
    ) -> float:
        """
        Estimate the price of the tasks
        Args:
            tasks: list of tasks to estimate
            price_per_mb: price per mb
        Returns:
            estimated price
        """

        total_len = 0
        for task in tasks:
            samples = self.generate_samples(task)["samples"]
            for sample in samples:
                total_len += len(sample)

        return (float(total_len) / 1024 / 1024) * price_per_mb

    def parse_results(self, task, results):
        terms = Counter()
        definitions = Counter()
        raw_translations = []
        parsed_results = []

        for r in results:
            answer = self._unwrap_results(r)
            parsed = self._parse_result(task, answer)
            terms.update(parsed["all_terms"])
            definitions.update(parsed["all_definitions"])
            raw_translations.append(answer)
            parsed_results.append(parsed)

        return {
            "raw": parsed_results,
            "terms": terms.most_common(),
            "definitions": definitions.most_common(),
            "raw_translations": raw_translations,
            "type": "translator",
        }

    def _parse_result(self, task: Dict, result: str) -> Dict:
        """
        A bunch of internal heuristics to parse the result of the translation
        Currently it's optimized for ukrainian language
        Args:
            task: original task
            result: result to parse
        Returns:
            dict with parsed terms and definitions
        """
        all_terms: List[str] = []
        all_definitions: List[str] = []

        for l in filter(None, result.replace("<br/>", "\n").split("\n")):
            for separator in [":", "–", "-", "—"]:
                if separator in l:
                    raw_terms, definition = l.split(separator, 1)
                    break
            else:
                logger.warning(
                    f"Cannot find a semicolon or dash in the translated text for task {task['_id']}"
                )
                continue

            terms: List[str] = list(map(str.strip, raw_terms.split(",")))

            if self.add_or:
                for or_word in ["чи то", "чи", "або", "альбо", "or"]:
                    splits = re.split(rf"[,\s]+{or_word}[,\s]+", terms[-1], flags=re.I)
                    if len(splits) > 1:
                        terms = terms[:-1] + list(map(lambda x: x.strip(", "), splits))
                        break
                else:
                    if self.group_by > 1 and len(task["words"]) > 1:
                        logger.warning(
                            f"Cannot find 'or' in the last chunk for task {task['_id']}"
                        )

            if self.add_quotes:
                terms = [term.strip('"\'"«»') for term in terms]

            all_terms += terms
            all_definitions.append(definition.strip())

        return {"all_terms": all_terms, "all_definitions": all_definitions}


class AbstractDictionaryTranslator(AbstractTranslator):
    """
    Abstract class for translators that use dictionary lookup
    """

    def generate_samples(self, task: Dict) -> Dict:
        """
        Generate samples for the dictionary lookup task
        Nothing fancy here, just return the list of words
        Args:
            task: task to generate samples for
        Returns:
            dict with the list of samples and the total number of lemmas + pos
        """
        return {
            "samples": list(task["words"].values()),
            "total_lemmas": len(task["words"]),
            "pos": task["pos"],
        }

    def translate(self, task: Dict, sleep_between_samples: float = 1):
        raise NotImplementedError()

    def parse_results(self, task: Dict, results: List[Dict]):
        raise NotImplementedError()

    def method_id(self) -> str:
        raise NotImplementedError()
