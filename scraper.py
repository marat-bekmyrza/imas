import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import pymysql
import datetime

URL = "https://tengrinews.kz"
NOW = datetime.datetime.now()
TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)

conn = pymysql.connect(host="localhost", port=3306, user="root", password="sqlpassword")
cursor = conn.cursor()


def init_db():
    # cursor.execute("CREATE DATABASE tengrinews;")
    cursor.execute("USE tengrinews")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS comments")
    sql = """CREATE TABLE items (
            id INT(11) NOT NULL,
            link VARCHAR(255) NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            publsih_date DATE NOT NULL,
            publish_datetime DATETIME NOT NULL,
            parse_date DATETIME NOT NULL,  
            PRIMARY KEY (id)
            )"""
    cursor.execute(sql)
    sql = """CREATE TABLE comments (
           id INT(11) NOT NULL,
           item_id INT(11) NOT NULL,
           author VARCHAR(255) NOT NULL, 
           date TEXT NOT NULL,
           content TEXT NOT NULL,
           parse_date DATETIME NOT NULL,
           PRIMARY KEY (item_id)
           )"""
    cursor.execute(sql)


def scrape():
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    results = soup.find('div', class_='tn-all_news tn-active')
    news_items = results.find_all('div', class_='tn-tape-item')

    driver = webdriver.Safari()
    # xpath = '//span[@tn-arrow="down"]'

    news_id, comment_id = 0, 0
    for news_item in news_items:
        try:
            link = ''.join([URL, news_item.find('a')['href']])
            driver.get(link)
            # driver.find_element_by_xpath(xpath).click()   # Not necessary

            news_page = driver.page_source  # bs4 doesn't return full html page
            news_soup = BeautifulSoup(news_page, 'html.parser')
            news_results = news_soup.find('div', class_='tn-content')

            title = news_results.find('h1', class_='tn-content-title').text
            title.replace("'", "''")
            publish_date = news_results.find('ul', class_='tn-data-list').find('time').text
            news_content = news_results.find('div', class_='tn-news-content')
            title_image = ''.join([URL, news_content.find('img')['src']])

            news_text = news_content.find('div', class_='tn-news-text')
            text = ''
            for p in news_text.find_all('p'):
                text = ''.join([text, p.get_text().strip() + ' '])
            text = text.replace("'", "''")

            comment_items = news_soup.find('div', class_='tn-comment-list').contents
            comment_authors, comment_dates, comment_contents = [], [], []
            for comment_item in comment_items:
                comment_authors.append(comment_item.find('span', 'tn-user-name').text)
                comment_dates.append(comment_item.find('time').text)
                comment_text = comment_item.find('div', class_='tn-comment-item-content-text').get_text()
                comment_contents.append(comment_text.replace("'", "''"))
        except:
            continue

        # today and yesterday are mostly enough for the recent news
        if 'сегодня' in publish_date:
            news_date = TODAY.strftime("%Y-%m-%d")
        elif 'вчера' in publish_date:
            news_date = YESTERDAY.strftime("%Y-%m-%d")

        news_datetime = news_date + " " + publish_date[-5:] + ":00"
        parse_datetime = NOW.strftime("%Y-%m-%d %H:%M:%S")

        sql = "INSERT INTO `items` VALUES (" + str(news_id) + ",'" + link + "','" + title + "','" + text + "','" +\
              news_date + "','" + news_datetime + "','" + parse_datetime + "');"
        cursor.execute(sql)
        for author, date, content in zip(comment_authors, comment_dates, comment_contents):
            sql = "INSERT INTO `comments` VALUES (" + str(news_id) + "," + str(comment_id) + ",'" + author + "','" + \
                  date + "','" + content + "','" + parse_datetime + "');"
            cursor.execute(sql)
            comment_id += 1
        news_id += 1

    driver.close()
    conn.commit()


init_db()
scrape()
