# -*- coding: utf-8 -*-
# !/usr/bin/env python3
from requests_html import HTMLSession
import pprint
import random
import string
import time
import hashlib
import json
import git
import re
import base64
import requests
from requests.adapters import HTTPAdapter, Retry
import os
import subprocess
import ssl
from pathlib import Path
ssl._create_default_https_context = ssl._create_unverified_context
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

global pipes
pipes = set()

class GetSrc:
    def __init__(self, username=None, token=None, url=None, repo=None, num=10, target=None, timeout=3, signame=None, jar_suffix=None, githubproxy=None):
        self.jar_suffix = jar_suffix if jar_suffix else 'jar'
        self.registry = 'github.com'
        self.mirror_proxy = os.getenv('githubproxy', 'https://gitproxy.6864.buzz/').rstrip('/')
        self.num = int(num)
        self.sep = os.path.sep
        self.username = username
        self.token = token
        self.timeout = timeout
        self.url = url
        self.repo = repo if repo else 'tvbox'
        self.target = f'{target.split(".json")[0]}.json' if target else 'tvbox.json'
        self.headers = {"user-agent": "okhttp/3.15 Html5Plus/1.0 (Immersed/23.92157)"}
        self.s = requests.Session()
        self.signame = signame
        retries = Retry(total=3, backoff_factor=1)
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))
        self.size_tolerance = 15
        self.main_branch = 'main'
        self.slot = f'{self.mirror_proxy}/{self.username}/{self.repo}/{self.main_branch}'

    # 保留原有功能方法，删除mirror相关逻辑
    def file_hash(self, filepath):
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def remove_duplicates(self, folder_path):
        folder_path = Path(folder_path)
        jar_folder = f'{folder_path}/jar'
        excludes = {'.json', '.git', 'jar', '.idea', 'ext', '.DS_Store', '.md'}
        files_info = {}

        self.rename_jar_suffix(jar_folder)

        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix not in excludes:
                file_size = file_path.stat().st_size
                file_hash = self.file_hash(file_path)
                files_info[file_path.name] = {'path': str(file_path), 'size': file_size, 'hash': file_hash}

        keep_files = []
        for file_name, info in sorted(files_info.items(), key=lambda item: item[1]['size']):
            if not keep_files or abs(info['size'] - files_info[keep_files[-1]]['size']) > self.size_tolerance:
                keep_files.append(file_name)
                self.remove_all_except_jar(jar_folder)
            else:
                os.remove(info['path'])
                self.remove_jar_file(jar_folder, file_name.replace('.txt', f'{self.jar_suffix}'))

        keep_files.sort()
        return keep_files

    def rename_jar_suffix(self, jar_folder):
        for root, _, files in os.walk(jar_folder):
            for file in files:
                old_file = os.path.join(root, file)
                new_file = os.path.join(root, os.path.splitext(file)[0] + f'.{self.jar_suffix}')
                os.rename(old_file, new_file)

    def remove_all_except_jar(self, jar_folder):
        for file_name in os.listdir(jar_folder):
            full_path = os.path.join(jar_folder, file_name)
            if os.path.isfile(full_path):
                _, ext = os.path.splitext(file_name)
                if ext != f'.{self.jar_suffix}':
                    self.remove_jar_file(jar_folder, file_name)

    def remove_jar_file(self, jar_folder, file_name):
        jar_path = os.path.join(jar_folder, file_name)
        if os.path.isfile(jar_path):
            os.remove(jar_path)

    def remove_emojis(self, text):
        emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"
                           u"\U0001F300-\U0001F5FF"
                           u"\U0001F680-\U0001F6FF"
                           u"\U0001F1E0-\U0001F1FF"
                           "\U00002500-\U00002BEF"
                           "\U00010000-\U0010ffff"
                           "\u200d\u20E3\ufe0f]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text.replace('/', '_').replace('多多', '').replace('┃', '').replace('线路', '').replace('匚','').strip())

    def json_compatible(self, text):
        return text.replace(' ', '').replace("'",'"').replace('key:', '"key":').replace('name:', '"name":'
                   ).replace('type:', '"type":').replace('api:','"api":').replace('searchable:', '"searchable":'
                   ).replace('quickSearch:', '"quickSearch":').replace('filterable:','"filterable":').strip()

    def ghproxy(self, text):
        return text.replace('https://raw.githubusercontent.com', self.mirror_proxy)

    def set_hosts(self):
        try:
            resp = requests.get('https://hosts.gitcdn.top/hosts.json', timeout=5)
            if resp.status_code == 200:
                for entry in resp.json():
                    if entry[1] == "github.com":
                        with open('/etc/hosts', 'r+') as f:
                            if entry[0] not in f.read():
                                f.write(f'\n{entry[0]} github.com')
                        break
        except Exception as e:
            pass

    def picparse(self, url):
        r = self.s.get(url, verify=False)
        matches = re.findall(r'([A-Za-z0-9+/]+={0,2})', r.text)
        return base64.b64decode(matches[-1]).decode('utf-8')

    def js_render(self, url):
        session = HTMLSession(browser_args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
        r = session.get(f'http://lige.unaux.com/?url={url}', timeout=min(self.timeout*4, 15), verify=False)
        r.html.render(timeout=min(self.timeout*4, 15))
        return r.html

    def get_jar(self, name, url, text):
        try:
            match = re.search(r'\"spider\":\s?\"([^,]+)\"', text)
            if match:
                jar_url = match.group(1).replace('./', f'{url}/').split(';')[0]
                jar_name = f"{name}.{self.jar_suffix}"
                jar_path = f'{self.repo}/jar/{jar_name}'
                
                content = self.s.get(jar_url, timeout=min(self.timeout*4, 15)).content
                with open(jar_path, 'wb') as f:
                    f.write(content)
                
                return text.replace(match.group(1), f'{self.slot}/jar/{jar_name}')
        except Exception as e:
            print(f'Jar下载失败: {e}')
        return text

    def download(self, url, name, filename, cang=True):
        try:
            path = os.path.dirname(url)
            r = self.s.get(url, headers=self.headers, verify=False, timeout=self.timeout)
            
            if r.status_code != 200 or 'searchable' not in r.text:
                r = self.js_render(url)
                if not r.text: r = self.picparse(url)
            
            content = r.text
            if 'searchable' in content:
                content = self.ghproxy(content.replace('./', f'{path}/'))
                content = self.get_jar(name, url, content)
                
                with open(f'{self.repo}/{filename}', 'w', encoding='utf-8') as f:
                    f.write(content)
                pipes.add(name)
                
                if cang:
                    return {'name': name, 'url': f'{self.slot}/{filename}'}
        except Exception as e:
            print(f'下载失败: {name} {url} - {e}')
        return None

    def down(self, data, s_name):
        items = []
        for u in data.get("urls", data.get("sites", [])):
            name = self.remove_emojis(u.get("name", "")).strip()
            filename = f'{name}.txt'
            
            if name not in pipes:
                item = self.download(u["url"], name, filename)
                if item: items.append(item)
        
        with open(f'{self.repo}/{s_name}', 'w', encoding='utf-8') as f:
            json.dump({'urls': items}, f, indent=4, ensure_ascii=False)

    def all(self):
        files = self.remove_duplicates(self.repo)
        items = [{'name': f.split('.')[0], 'url': f'{self.slot}/{f}'} for f in files]
        
        with open(f'{self.repo}/all.json', 'w', encoding='utf-8') as f:
            json.dump({'urls': items}, f, indent=4, ensure_ascii=False)

    def batch_handle_online_interface(self):
        print('--------- 开始处理在线接口 ----------')
        for url in self.url.split(','):
            parts = url.split('?&signame=')
            self.url, self.signame = parts[0], parts[1] if len(parts)>1 else None
            self.storeHouse()

    def git_clone(self):
        if os.path.exists(self.repo):
            subprocess.run(['rm', '-rf', self.repo], check=True)
        
        try:
            repo_url = f'https://{self.token}@github.com/{self.username}/{self.repo}.git'
            repo = git.Repo.clone_from(repo_url, self.repo, depth=1)
            os.makedirs(f'{self.repo}/jar', exist_ok=True)
            return self.get_local_repo()
        except Exception as e:
            print(f'克隆失败: {e}')
            exit(1)

    def get_local_repo(self):
        repo = git.Repo(self.repo)
        with repo.config_writer() as cw:
            cw.set_value('user', 'name', self.username)
            cw.set_value('user', 'email', self.username)
            cw.set_value('http', 'postBuffer', '524288000')
        
        for branch in repo.remote().refs:
            if branch.name in ['origin/main', 'origin/master']:
                self.main_branch = branch.name.split('/')[-1]
                break
        
        self.slot = f'{self.mirror_proxy}/{self.username}/{self.repo}/{self.main_branch}'
        return repo

    def git_push(self, repo):
        try:
            repo.git.add(A=True)
            repo.git.commit(m='update')
            repo.git.push()
        except Exception as e:
            print(f'推送失败: {e}')
        
        try:
            repo.git.checkout('--orphan', 'tmp_branch')
            repo.git.add(A=True)
            repo.git.commit(m='clean')
            repo.git.branch('-D', self.main_branch)
            repo.git.branch('-m', self.main_branch)
            repo.git.push('-f', 'origin', self.main_branch)
        except Exception as e:
            print(f'清理提交历史失败: {e}')

    def storeHouse(self):
        try:
            resp = self.s.get(self.url, timeout=self.timeout, verify=False)
            content = resp.text
        except:
            content = self.js_render(self.url).text or self.picparse(self.url)
        
        content = self.json_compatible(content)
        
        if 'searchable' in content:
            filename = f'{self.signame or "unknown"}.txt'
            with open(f'{self.repo}/{filename}', 'w') as f, open(f'{self.repo}/{self.target}', 'w') as f2:
                processed = self.get_jar(filename.split('.')[0], self.url, self.ghproxy(content))
                f.write(processed)
                f2.write(processed)
            return
        
        try:
            data = json.loads(content)
            if 'storeHouse' in data:
                items = []
                for s in data['storeHouse'][:self.num]:
                    s_name = f'{self.remove_emojis(s["sourceName"])}.json'
                    self.down(s, s_name)
                    items.append({'sourceName': s_name[:-5], 'sourceUrl': f'{self.slot}/{s_name}'})
                
                with open(f'{self.repo}/{self.target}', 'w') as f:
                    json.dump({'storeHouse': items}, f, indent=4, ensure_ascii=False)
            else:
                self.down(data, self.target)
        except Exception as e:
            print(f'解析仓库失败: {e}')

    def replace_proxy_urls(self):
        pattern = re.compile(r'(https?://(raw\.githubusercontent\.com|github\.com/[^/]+/[^/]+/raw)/[^\s\'"]+)')
        for root, _, files in os.walk(self.repo):
            for file in files:
                if file.endswith(('.txt', '.json')):
                    path = os.path.join(root, file)
                    with open(path, 'r+') as f:
                        content = f.read()
                        content = pattern.sub(f'{self.mirror_proxy}/\\1', content)
                        f.seek(0)
                        f.write(content)
                        f.truncate()

    def run(self):
        start = time.time()
        self.set_hosts()
        repo = self.git_clone()
        self.batch_handle_online_interface()
        self.replace_proxy_urls()
        self.all()
        self.git_push(repo)
        print(f'''耗时: {time.time()-start:.2f}s
        ############ 配置地址 ############
        {self.slot}/all.json
        {self.slot}/{self.target}''')

if __name__ == '__main__':
    GetSrc(
        username=os.getenv('username') or os.getenv('u'),
        token=os.getenv('token'),
        url=os.getenv('url'),
        repo=os.getenv('repo'),
        num=int(os.getenv('num', 10)),
        target=os.getenv('target'),
        timeout=int(os.getenv('timeout', 3)),
        signame=os.getenv('signame'),
        jar_suffix=os.getenv('jar_suffix'),
    ).run()
