import hashlib
import requests
from lxml import etree
from lxml.html import tostring
import json
import time
import re
from config import Q, HEADERS
from concurrent.futures import ProcessPoolExecutor


def get_index_page():
    url = f'https://tieba.baidu.com/f?kw={Q}&ie=utf-8&pn=0'
    first_html = parse_index(url)
    page_url = 'https:' + first_html.xpath('.//div[@id="frs_list_pager"]//a[last()]/@href')[0]
    last_html = parse_index(page_url)
    page_num = last_html.xpath('.//div[@id="frs_list_pager"]//span/text()')[0]
    return page_num


def parse_index(url):
    while True:
        try:
            s = requests.Session()
            response = s.get(url, headers=HEADERS)
            html = etree.HTML(response.text)
            return html
        except:
            print("请求出错，开始重试...")
            time.sleep(5)
            continue


def author_data(name_input):
    url = f'http://tieba.baidu.com/home/get/panel?ie=utf-8&un={name_input}'
    while True:
        try:
            response = requests.get(url, headers=HEADERS, timeout=5)
            j = json.loads(response.text, encoding='utf8')
            # print(data['data'])
            if j['error'] == '成功':
                data = j['data']
                user_id = data['id']
                user_name = data['name']
                name_show = data['name_show']
                portrait = data['portrait']
                sex = data['sex']
                tb_age = data['tb_age']
                return (user_id, user_name, name_show, portrait, sex, tb_age)
            else:
                return (None, None, None, None, None, None)
        except:
            print("请求出错，开始重试...")
            time.sleep(5)
            continue


def get_index(url):
    html = parse_index(url)
    lis = html.xpath('//*[@id="thread_list"]/li[@class=" j_thread_list clearfix"]')
    for li in lis:
        # data-tid(用于访问评论api获取子评论)
        data_tid = li.xpath('./@data-tid')[0]
        # 获取详情链接并访问
        url = li.xpath('.//div[contains(@class,"threadlist_title")]/a/@href')[0]
        comment_url = 'https://tieba.baidu.com' + url
        # 获取评论页数据，（1楼时间，评论页数）
        data = get_c_page_data(comment_url)
        if data:
            # 评论页数
            #         data[1]
            for page in range(int(data[1])):
                print(f'开始搜索第{page + 1}页评论')
                comment_url = 'https://tieba.baidu.com' + url + f'?pn={page + 1}'
                # 获取评论
                get_comment(comment_url, data_tid)


def get_comment(comment_url, data_tid):
    comment_html = parse_index(comment_url)
    div_list = comment_html.xpath('//*[@id="j_p_postlist"]//div[contains(@class,"l_post_bright")]')
    c_num = 1
    for div in div_list:
        print(f'开始搜索第{c_num}个评论')
        # data-pid / post_id
        data_pid = div.xpath('./@data-pid')[0]
        # 获取子评论页数
        page_num = get_child_comment_page(data_tid, data_pid)
        if page_num:
            for i in range(1, int(page_num)+1):
                child_comment(data_tid, data_pid, i)
            c_num += 1
        else:
            child_comment(data_tid, data_pid, 1)
            c_num += 1


def get_child_comment_page(data_tid, data_pid):
    url = f'https://tieba.baidu.com/p/comment?tid={data_tid}&pid={data_pid}&pn=1'
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                #         print(response.text)
                html = etree.HTML(response.text)
                if html.xpath('//li[contains(@class,"lzl_li_pager")]//p[contains(@class,"j_pager")]/span[@class="tP"]'):
                    page_num = html.xpath('//li[contains(@class,"lzl_li_pager")]//p[contains(@class,"j_pager")]//a[last()]/@href')[0][1:]
                    return page_num
                else:
                    return None
        except:
            print('请求出错，开始重试...')
            time.sleep(5)
            continue


def child_comment(data_tid, data_pid, page_num):
    url = f'https://tieba.baidu.com/p/comment?tid={data_tid}&pid={data_pid}&pn={page_num}'
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                html = etree.HTML(response.text)
                li_list = html.xpath('//li[contains(@class, "lzl_single_post")]')
                if li_list:
                    count = len(li_list)
                    print('有子评论')
                    md_num = 0
                    for li in li_list:
                        child_comment = {}
                        print("-----------------------------------------------------------")
                        start = int(round(time.time() * 1000))
                        # 用户名
                        if li.xpath('.//div[@class="lzl_cnt"]/a/text()'):
                            name_input = li.xpath('.//div[@class="lzl_cnt"]/a/text()')[0]
                        else:
                            por = li.xpath('./@data-field')[0]
                            id = json.loads(por)
                            id = id['portrait']
                            user_url = f'http://tieba.baidu.com/home/main?ie=utf-8&id={id}'
                            while True:
                                try:
                                    response = requests.get(user_url)
                                    html = etree.HTML(response.text)
                                    if html.xpath('//div[@id="userinfo_wrap"]//div[@class="userinfo_title"]/span/text()'):
                                        name_input = html.xpath('//div[@id="userinfo_wrap"]//div[@class="userinfo_title"]/span/text()')[0]
                                        break
                                    else:
                                        name_input = ''
                                        break
                                except:
                                    print('连接错误')
                                    time.sleep(5)
                                    continue
                        # 调用author_data
                        data = author_data(name_input)
                        # user_id
                        user_id = data[0]
                        print('user_id:', user_id)
                        # user_name
                        user_name = data[1]
                        print('user_name:', user_name)
                        # name_show
                        name_show = data[2]
                        print('name_show:', name_show)
                        # portrait
                        portrait = data[3]
                        print('portrait:', portrait)
                        # sex
                        sex = data[4]
                        print('sex:', sex)
                        # tb_age
                        tb_age = data[5]
                        print('tb_age:', tb_age)
                        # 时间
                        r_time = li.xpath('.//div[@class="lzl_content_reply"]//span[last()]/text()')[0]
                        print(r_time)
                        # 评论
                        content = li.xpath('.//div[@class="lzl_cnt"]//span[@class="lzl_content_main"]')[0]
                        text = re.compile('<.*?>').sub('', tostring(content, encoding='utf8', pretty_print=True, method='html').decode('utf8')).strip()
                        print(text)
                        end = int(round(time.time() * 1000))
                        print("-----------------------------------------------------------")
                        # child_comment['user_name'] = user_name
                        # child_comment['name_show'] = name_show
                        # child_comment['user_id'] = user_id
                        # child_comment['portrait'] = portrait
                        # child_comment['sex'] = sex
                        # child_comment['tb_age'] = tb_age
                        # child_comment['post_id'] = data_pid
                        # child_comment['r_time'] = r_time
                        # child_comment['text'] = text
                        # 正文
                        child_comment['content'] = text
                        # 标题
                        child_comment['title'] = text
                        # 链接
                        child_comment['url'] = url
                        # 域名
                        child_comment['domain'] = 'tieba.baidu.com'
                        # 爬虫id
                        child_comment['spiderUUID'] = ''
                        # 模板id
                        child_comment['spiderInfoId'] = 'AWyKbK5DV6BZazZ68DkJ'
                        # 分类
                        child_comment['category'] = ''
                        # 网页快照
                        child_comment['rawHTML'] = ''
                        # 关键词
                        child_comment['keywords'] = []
                        # 摘要
                        child_comment['summary'] = []
                        # 抓取时间
                        child_comment['gatherTime'] = int(round(time.time() * 1000))
                        # 网页id，自动分配的
                        md5_base = url + data_pid + str(md_num)
                        child_comment['id'] = hashlib.md5(md5_base.encode(encoding='utf8')).hexdigest()
                        # 发布时间
                        child_comment['publishTime'] = r_time+':00'
                        # 命名实体
                        child_comment['namedEntity'] = {}
                        # 动态字段
                        dynamicFields = {}
                        dynamicFields['user_name'] = user_name
                        dynamicFields['name_show'] = name_show
                        dynamicFields['user_id'] = user_id
                        dynamicFields['portrait'] = portrait
                        dynamicFields['sex'] = sex
                        dynamicFields['tb_age'] = tb_age
                        dynamicFields['data_tid'] = data_tid
                        dynamicFields['data_pid'] = data_pid
                        child_comment['dynamicFields'] = dynamicFields
                        # 本网页处理时长
                        child_comment['processTime'] = end-start
                        print(child_comment)
                        to_json(child_comment)
                        md_num += 1
                    if count == md_num:
                        break
                else:
                    print('没有回复')
                    break
        except:
            print('请求出错，开始重试...')
            time.sleep(5)
            continue


def get_c_page_data(comment_url):
    comment_html = parse_index(comment_url)
    if comment_html.xpath('//*[@id="j_p_postlist"]//div[contains(@class,"l_post_bright")]'):
        div_list = comment_html.xpath('//*[@id="j_p_postlist"]//div[contains(@class,"l_post_bright")]')
        # 获取一楼的时间返回给主页面
        p_time = div_list[0].xpath('.//div[@class="post-tail-wrap"]/span[last()]/text()')[0]
        page_count = comment_html.xpath('//div[@class="l_thread_info"]//ul[@class="l_posts_num"]//li[@class="l_reply_num"]/span[last()]/text()')[0]
        return p_time, page_count
    else:
        return None


def to_json(comment):
    with open('tieba_reply.json', 'a', encoding='utf8') as f:
        # with open('E:/tieba.json', 'a', encoding='utf8') as f:
        f.write(json.dumps(comment, ensure_ascii=False) + '\n')
    print('插入成功')


if __name__ == '__main__':
    page_num = get_index_page()
    print(f'总共有{page_num}页')
    pool = ProcessPoolExecutor(3)
    for i in range(0, int(page_num)):
        url = f'https://tieba.baidu.com/f?kw={Q}&ie=utf-8&pn={i*50}'
        pool.submit(get_index, url)
    pool.shutdown(wait=True)