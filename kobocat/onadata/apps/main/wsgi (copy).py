from django.core.wsgi import get_wsgi_application
import os

os.environ.setdefault("PROFILE_PATH", "/home/vagrant/.profile")
os.environ.setdefault("V_R", "/home/vagrant")
os.environ.setdefault("V_E", "/home/vagrant/env")
os.environ.setdefault("V_S", "/home/vagrant/scripts")
os.environ.setdefault("V_L", "/home/vagrant/logs")
os.environ.setdefault("SRC_DIR", "/home/vagrant/src_csvp")
os.environ.setdefault("HTTP_PROTOCOL", "http")
os.environ.setdefault("PIP_DOWNLOAD_CACHE", "/home/vagrant/.pip_cache")
os.environ.setdefault("SERVER_IP", "127.0.0.1")
os.environ.setdefault("ip", "csvp.mpower-social.com")
os.environ.setdefault("KOBOFORM_URL", "http://csvp.mpower-social.com:8000")
os.environ.setdefault("KOBOFORM_SERVER_PORT", "8000")
os.environ.setdefault("KOBOCAT_URL", "http://csvp.mpower-social.com:8004")
os.environ.setdefault("KOBOCAT_SERVER_PORT", "8004")
os.environ.setdefault("KOBOCAT_INTERNAL_URL", "http://csvp.mpower-social.com:8004")
os.environ.setdefault("ENKETO_EXPRESS_SERVER_PORT", "80")
os.environ.setdefault("KOBOCAT_REPO", "https://github.com/kobotoolbox/kobocat.git")
os.environ.setdefault("KOBOCAT_BRANCH", "master")
os.environ.setdefault("KOBOCAT_PATH", "/home/vagrant/src_csvp/kobocat")
os.environ.setdefault("KOBOCAT_TEMPLATES_REPO", "https://github.com/kobotoolbox/kobocat-template.git")
os.environ.setdefault("KOBOCAT_TEMPLATES_BRANCH", "master")
os.environ.setdefault("KOBOCAT_TEMPLATES_PATH", "/home/vagrant/src_csvp/kobocat-template")
os.environ.setdefault("KOBOFORM_PREVIEW_SERVER", "http://csvp.mpower-social.com:8000")
os.environ.setdefault("KOBOFORM_REPO", "https://github.com/kobotoolbox/dkobo.git")
os.environ.setdefault("KOBOFORM_BRANCH", "master")
os.environ.setdefault("KOBOFORM_PATH", "/home/vagrant/src_csvp/koboform")
os.environ.setdefault("PSQL_ADMIN", "postgres")
os.environ.setdefault("KOBO_PSQL_DB_NAME", "csvp")
os.environ.setdefault("KOBO_PSQL_DB_USER", "mpower")
os.environ.setdefault("KOBO_PSQL_DB_PASS", "DB@mPower@786")
os.environ.setdefault("DATABASE_SERVER_IP", "192.168.19.88")
os.environ.setdefault("DATABASE_URL", "postgis://kobo:kobo@192.168.19.88:5432/csvp")
os.environ.setdefault("DEFAULT_KOBO_USER", "mpower")
os.environ.setdefault("DEFAULT_KOBO_PASS", "DB@mPower@786")
os.environ.setdefault("ENKETO_EXPRESS_REPO_DIR", "/home/vagrant/src_csvp/enketo-express")
os.environ.setdefault("ENKETO_EXPRESS_UPDATE_REPO", "false")
os.environ.setdefault("ENKETO_SERVER", "http://csvp.mpower-social.com")
os.environ.setdefault("ENKETO_PREVIEW_URI", "/preview")
os.environ.setdefault("ENKETO_URL", "http://csvp.mpower-social.com")
os.environ.setdefault("ENKETO_API_ROOT", "/api/v2")
os.environ.setdefault("ENKETO_OFFLINE_SURVEYS", "True")
os.environ.setdefault("ENKETO_API_ENDPOINT_PREVIEW", "/preview")
os.environ.setdefault("ENKETO_PROTOCOL", "http")
os.environ.setdefault("ENKETO_API_TOKEN", "enketorules")
os.environ.setdefault("SENDER_MANAGER_PATH","/home/vagrant/src_csvp/messagesender")
os.environ.setdefault("SENDER_MANAGER_HOST", "csvp.mpower-social.com")
os.environ.setdefault("SENDER_MANAGER_PORT", "1884")
os.environ.setdefault("SENDER_MANAGER_DATABASE_SCHEMA", "csvp")
os.environ.setdefault("SENDER_MANAGER_DATABASE_HOST", "192.168.19.88")
os.environ.setdefault("SENDER_MANAGER_DATABASE_PORT", "5432")
os.environ.setdefault("SENDER_MANAGER_DATABASE_USER", "mpower")
os.environ.setdefault("SENDER_MANAGER_DATABASE_PWD", "DB@mPower@786")
os.environ.setdefault("DJANGO_LIVE_RELOAD", "False")
os.environ.setdefault("DJANGO_SITE_ID", "1")
os.environ.setdefault("DJANGO_SECRET_KEY", "P2Nerc3oG2564z5mHTGUhAoh2CzOMVenWBNMNWgWU796n")
os.environ.setdefault("CLEAN_APT_CACHE", "True")
os.environ.setdefault("AUTOLAUNCH", "1")
os.environ.setdefault("PYTHONPATH", "/home/vagrant/env:")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kobocat_settings")



application = get_wsgi_application()