import os
from feedtool import VikaApi, read_rss

api = os.environ.get("API")
clipper = os.environ.get("Clipper")
feeds = os.environ.get("Feeds")


def run():
    if api is None:
        print("api secrets is not set!")
        return
    rss_list = VikaApi(api, clipper, feeds)

    read_rss(rss_list)


if __name__ == "__main__":
    run()
