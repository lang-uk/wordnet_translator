"""
A client for Bing translator/dictionary API
"""

from typing import List, Dict
import json
import uuid
from urllib.parse import urljoin

import requests

from .exc import BingTranslationException
from .constants import ENGLISH, UKRAINIAN


class BingTranslatorClient:
    """
    Bing translator client
    """

    translate_path: str = "/translate"
    dictionary_lookup_path: str = "/dictionary/lookup"

    def __init__(
        self,
        key_file: str,
        endpoint: str = "https://api.cognitive.microsofttranslator.com",
    ):
        self.endpoint: str = endpoint

        with open(key_file, "r", encoding="utf8") as fp:
            self.headers = json.load(fp)

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for the request
        """
        headers = self.headers.copy()
        headers["X-ClientTraceId"] = str(uuid.uuid4())

        return headers

    def _request(
        self,
        path: str,
        phrase: str,
        source_language: str = ENGLISH,
        target_language: str = UKRAINIAN,
    ) -> Dict:
        """
        A service method to make a request to the API, wrapping all the logic for bing API
        """
        constructed_url = urljoin(self.endpoint, path)

        headers = self._get_headers()
        params = {"api-version": "3.0", "from": source_language, "to": target_language}

        body = [{"text": phrase}]

        request = requests.post(
            constructed_url, params=params, headers=headers, json=body, timeout=60
        )

        try:
            response = request.json()
        except json.JSONDecodeError as exc:
            raise BingTranslationException(
                f"Cannot translate phrase '{phrase}' cannot parse the response as json"
            ) from exc

        if "error" in response:
            raise BingTranslationException(
                f"Cannot translate phrase '{phrase}' because of an error: {response['error']}"
            )

        if request.status_code != 200:
            raise BingTranslationException(
                f"Cannot translate phrase '{phrase}', status code was {request.status_code}"
            )

        return response

    def translate(
        self,
        phrase: str,
        source_language: str = ENGLISH,
        target_language: str = UKRAINIAN,
    ) -> str:
        """
        Translate a phrase using bing translator
        Args:
            phrase: phrase to translate
            source_language: source language
            target_language: target language
        Returns:
            translated phrase (first variant)
        """
        response = self._request(
            self.translate_path, phrase, source_language, target_language
        )

        for l in response:
            for translation in l.get("translations", []):
                return translation["text"]

        raise BingTranslationException(
            f"Cannot find a translation for a phrase '{phrase}'"
        )

    def dictionary_lookup(
        self,
        word: str,
        source_language: str = ENGLISH,
        target_language: str = UKRAINIAN,
    ) -> List:
        """
        Lookup a word in dictionary
        Args:
            word: word to lookup
            source_language: source language
            target_language: target language
        Returns:
            list of translations
        """
        response = self._request(
            self.dictionary_lookup_path, word, source_language, target_language
        )

        for l in response:
            return l.get("translations", [])

        raise BingTranslationException(
            f"Cannot find a translation for a phrase '{word}'"
        )
