class DandiRedirectUrl:
    """
    This class is used to get the redirect URL of a DANDI asset. It allows
    remfile to be used with embargoed DANDI assets.
    The URL will auto-renew and effectively never expire.

    Author: Jeremy Magland

    Example usage
    -------------
    import remfile
    import os
    dandi_api_key = os.environ.get('DANDI_API_KEY')
    url_redirect = DandiRedirectUrl(url, dandi_api_key)
    remf = remfile.File(url_redirect)
    """
    def __init__(self, api_url: str, dandi_api_key=None) -> None:
        self._api_url = api_url
        self._dandi_api_key = dandi_api_key
        self._redirect_url = ''
        self._timestamp = 0
    def get_url(self):
        import requests
        import time
        elapsed = time.time() - self._timestamp
        if elapsed > 60 * 10:
            headers = {}
            if self._dandi_api_key:
                headers['Authorization'] = f'token {self._dandi_api_key}'
            response = requests.head(self._api_url, headers=headers, allow_redirects=False)
            response.raise_for_status()
            self._redirect_url = response.headers['Location']
            self._timestamp = time.time()
        return self._redirect_url