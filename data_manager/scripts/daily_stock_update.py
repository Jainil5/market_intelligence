from data_manager.services.stock_updater import update_all_stocks
from data_manager.services.news_updater import update_news_for_all_stocks
from data_manager.services.announcement_updater import update_announcements_for_all_stocks

if __name__ == "__main__":
    print({"prices": update_all_stocks(include_fundamentals=True)})
    print({"news": update_news_for_all_stocks()})
    print({"announcements": update_announcements_for_all_stocks()})
