"""
The implementation of the wordnet translator using Google translator API
"""

from typing import Dict, List
from time import sleep
import html

from google.cloud import translate_v2 as translate
from .abstract import AbstractSlidingWindowTranslator
from .constants import ENGLISH, UKRAINIAN


class SlidingWindowGoogleTranslator(AbstractSlidingWindowTranslator):
    """
    The implementation of the wordnet translator using Google translator API
    """

    def __init__(
        self,
        gcloud_credentials: str,
        group_by: int = 3,
        add_or: bool = True,
        add_quotes: bool = True,
        combine_in_one=True,
        add_aux_words=True,
        source_language: str = ENGLISH,
        target_language: str = UKRAINIAN,
    ) -> None:
        """
        Args:
            gcloud_credentials: path to the google cloud credentials
            **kwargs from the AbstractSlidingWindowTranslator
        Returns:
            None
        """
        self.gtrans_client = translate.Client.from_service_account_json(
            gcloud_credentials
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

    def translate(self, task: Dict, sleep_between_samples: float=1) -> Dict:
        results = []
        sampled = self.generate_samples(task)
        for sample in sampled["samples"]:
            results.append(
                self.gtrans_client.translate(
                    sample,
                    source_language=self.source_language,
                    target_language=self.target_language,
                )
            )
            sleep(sleep_between_samples)

        return self.parse_results(task, results)

    def _unwrap_results(self, response: Dict) -> str:
        return html.unescape(response.get("translatedText", ""))

    def estimate_tasks(self, tasks: List[Dict], price_per_mb: float=20) -> float:
        return super().estimate_tasks(tasks, price_per_mb)
