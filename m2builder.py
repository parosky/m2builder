#!/usr/bin/env python
# -*- coding: utf-8 -*-

import settings
import random
import twopy
import re
import wordpress_xmlrpc
import os
import sys

re_res = re.compile('>>[0-9]+')
re_link = re.compile(r'([^"]|^)(https?|ftp)(://[\w:;/.!?%#&=+-]+)')
re_sssp = re.compile(r'([^"]|^)(sssps?|ftp)(://[\w:;/.!?%#&=+-]+)')
re_img = re.compile(r'([^"]|^)(https?)(://[\w:;/.?%#&=+-]+\.(jpg|jpeg|png|gif|JPG|JPEG|PNG|GIF))')
self_path = os.path.dirname(os.path.abspath( __file__ ))

def make_use_tree(res):
    """ is_use -> 1 for all responses in the tree """ 
    res.is_use = True
    for r in res.res_from + res.res_to: 
        if r.is_use == False:
            make_use_tree(r)

def count_use(thread):
    """ count the number of responces with is_use == True """
    return len([res for res in thread if res.is_use == True])

def make_html_res(res):
    """ make html of one response """ 
    if res.is_used:
        return ""
    else:
        res.is_used = True
    rp = [make_html_res(r) for r in res.res_from]
    html = open('%s/res.html' % self_path).read().decode('utf-8')
    html = html.replace('<number>', str(res.number))
    html = html.replace('<name>', res.name)
    html = html.replace('<id>', res.ID)
    html = html.replace('<date>', res.date)
    html = html.replace('<rep_num>', str(min(len(res.res_from), 5)))
    html = html.replace('<body>', fix_body(res.body))
    html = html.replace('<res>', "\n".join(rp))
    return html

def make_html_thread(thread):
    """ make whole html of thread """
    html = []
    for res in thread:
        if res.is_use:
            html.append(make_html_res(res))
    return "\n".join(html)

def fix_body(body):
    """ translate body text from dat style to html style """
    return make_img_tag(remove_sssp(link_url((body.replace('\n', '<br>')))))

def link_url(str):
    """ make hyperlink """
    return re_link.sub(r'\1<a href="\2\3" target="_blank">\2\3</a>', str)

def remove_sssp(str):
    """ remove sssp """
    return re_sssp.sub(r'', str)

def make_img_tag(str):
    """ make img tags """
    return re_img.sub(r'\1<img class="res-img" src="\2\3"/>', str)

def post_to_wordpress(title, content1, content2=None):
    """ post to wordpress via xml-rpc """
    wpurl = settings.wordpress['url']
    client = wordpress_xmlrpc.Client(wpurl, settings.wordpress['user'], settings.wordpress['password'])
    post = wordpress_xmlrpc.methods.posts.WordPressPost()
    post.title = title
    post.description = content1
    if content2:
        post.extended_text = content2
    client.call(wordpress_xmlrpc.methods.posts.NewPost(post,True))

def run():
    """ main function """
    
    # get popular thread
    board = twopy.Board(random.choice(settings.crawl.values()))
    board.retrieve()
    for thread in board:
        if thread.res > 200:
            break
    thread.retrieve()
   
    # initialize properties
    for res in thread:
        res.res_to = []
        res.res_from = []
        res.is_use = False
        res.is_used = False

    # get replay relations
    for res in thread:
        rs = re_res.findall(res.body)
        for r in rs:
            num = int(r[2:])
            if num >= res.number:
                continue
            if num >= thread.res:
                continue
            res.res_to.append(thread[num])
            thread[num].res_from.append(res)

    # make use-tree of popular response
    thread[1].is_use = True
    for res in thread:
        if len(res.res_from)>=settings.min_popular_res:
            make_use_tree(res)

    # volume adjustment
    while count_use(thread) < settings.min_num_res:
        make_use_tree(random.choice(thread))

    # make html
    html = make_html_thread(thread)

    # post to wordpress
    pos = html.index('<div class="res', 100)
    post_to_wordpress(thread.title, html[:pos], html[pos:])

if __name__ == '__main__':
    run()
