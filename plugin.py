# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import time
from datetime import datetime
import urllib
import json
# third-party
import requests
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify, session, send_from_directory 
from flask_socketio import SocketIO, emit, send
from flask_login import login_user, logout_user, current_user, login_required

# sjva 공용

from framework.logger import get_logger
from framework import app, db, scheduler, path_data, socketio, check_api
from framework.util import Util, AlchemyEncoder
from system.logic import SystemLogic
from system.model import ModelSetting as SystemModelSetting


# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

# 패키지
from .model import ModelSetting
from .logic import Logic
from .logic_normal import LogicNormal


#########################################################


#########################################################
# 플러그인 공용                                       
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
menu = {
    'main' : [package_name, 'AV Agent'],
    'sub' : [
        ['setting', '설정'], ['log', '로그']
    ],
    'category' : 'plex'
}

plugin_info = {
    'version' : '0.1.0.0',
    'name' : 'av_agent',
    'category_name' : 'plex',
    'developer' : 'soju6jan',
    'description' : 'Plex SJVA AV Agent와 연동하는 플러그인',
    'home' : 'https://github.com/soju6jan/av_agent',
    'more' : '',
}


def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()



#########################################################
# WEB Menu 
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/setting' % package_name)

@blueprint.route('/<sub>')
@login_required
def first_menu(sub): 
    if sub == 'setting':
        arg = ModelSetting.to_dict()
        arg['package_name'] = package_name
        arg['agent_server'] = SystemModelSetting.get('ddns') + '/%s/api' % package_name
        return render_template('%s_setting.html' % package_name, sub=sub, arg=arg)
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI                                                            
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    # 설정 저장
    import framework.common.fileprocess as FileProcess
    try:
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            LogicNormal.proxy_init()
            return jsonify(ret)
        elif sub == 'test':
            #import framework.common.fileprocess as FileProcess
            #logger.debug('GGGGGGGGGGGGGGGGGG')
            logger.debug(FileProcess.proxies)
            ret = LogicNormal.test(request)
            return jsonify(ret)
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

#########################################################
# API - 외부
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
@check_api
def api(sub):
    try:
        import framework.common.fileprocess as FileProcess
        if sub == 'search':
            arg = request.args.get('code')
            ret = FileProcess.search(arg)
            ret = list(reversed(ret))
        elif sub == 'update':
            logger.debug(FileProcess.proxies)
            arg = request.args.get('code')
            ret = FileProcess.update(arg, use_discord_proxy=ModelSetting.get_bool('use_discord_proxy'))
        elif sub == 'image':
            from PIL import Image
            import requests
            # 2020-06-02 proxy 사용시 포스터처리
            image_url = request.args.get('url')
            logger.debug(image_url)
            method = ModelSetting.get('javdb_landscape_poster')
            if method == '0':
                if FileProcess.proxies is None:
                    return redirect(image_url)
                else:
                    im = Image.open(requests.get(image_url, stream=True, proxies=FileProcess.proxies).raw)
                    filename = os.path.join(path_data, 'tmp', 'rotate.jpg')
                    im.save(filename)
                    return send_file(filename, mimetype='image/jpeg')
            
            im = Image.open(requests.get(image_url, stream=True, proxies=FileProcess.proxies).raw)
            width,height = im.size
            logger.debug(width)
            logger.debug(height)
            if height > width * 1.5:
                return redirect(image_url)
            if method == '1':
                if width > height:
                    im = im.rotate(-90, expand=True)
            elif method == '2':
                if width > height:
                    im = im.rotate(90, expand=True)
            elif method == '3':
                new_height = int(width * 1.5)
                new_im = Image.new('RGB', (width, new_height))
                new_im.paste(im, (0, int((new_height-height)/2)))
                im = new_im

            filename = os.path.join(path_data, 'tmp', 'rotate.jpg')
            im.save(filename)
            return send_file(filename, mimetype='image/jpeg')
        elif sub == 'image_proxy':
            import framework.common.fileprocess as FileProcess
            from PIL import Image
            import requests
            image_url = request.args.get('url')
            logger.debug('image_url : %s', image_url)
            im = Image.open(requests.get(image_url, stream=True, verify=False, proxies=FileProcess.proxies).raw)
            filename = os.path.join(path_data, 'tmp', 'proxy.jpg')
            im.save(filename)
            return send_file(filename, mimetype='image/jpeg')
        elif sub == 'discord_proxy':
            from framework.common.notify import discord_proxy_image
            image_url = request.args.get('url')
            ret = discord_proxy_image(image_url, webhook_url=ModelSetting.get('discord_proxy_webhook_url'))
            logger.debug(ret)
            return redirect(ret)
        return jsonify(ret)
        
    except Exception as e:
        logger.debug('Exception:%s', e)
        logger.debug(traceback.format_exc())


"""
@blueprint.route('/avgle/<mode>', methods=['GET', 'POST'])
def avgle(mode):
    try:
        if mode == 'search':
            try:
                arg = request.args.get('arg')
                ret = Logic.avgle_search(arg)
                return jsonify(ret)
            except Exception as e:
                logger.debug('Exception:%s', e)
                logger.debug(traceback.format_exc())  
        elif mode == 'update':
            try:
                arg = request.args.get('arg')
                ret = Logic.avgle_update(arg)
                return jsonify(ret)
            except Exception as e:
                logger.debug('Exception:%s', e)
                logger.debug(traceback.format_exc())  
        
    except Exception as e:
        logger.debug('Exception:%s', e)
        logger.debug(traceback.format_exc())
        return 'fail'
"""
