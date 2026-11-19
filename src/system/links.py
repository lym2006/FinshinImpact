"""在线地址与协议头

- Pages 基址、发布接口路径与请求头
"""

_ACCOUNT = "FinshinLabs"
_MAIN_REPO = "FinshinImpact"

PAGES_BASE_URL = f"https://{_ACCOUNT}.github.io"
API_BASE_URL = "https://api.github.com"

# 本体读的三份远端内容
VERSION_PAGE_PATH = f"/{_MAIN_REPO}/pyproject.toml"
CATALOG_PATH = f"/{_MAIN_REPO}/adapters.toml"
RELEASES_PAGE_PATH = (
    f"/repos/{_ACCOUNT}/{_MAIN_REPO}/releases?per_page={{size}}&page={{page}}"
)

# 请求头值，GitHub 认 UA，缺头即拒
API_USER_AGENT = "Python-Script"

HTTP_SCHEME = "http://"
HTTPS_SCHEME = "https://"
