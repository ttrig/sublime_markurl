
'''@package Markurl

	- Lab
	- Sublime plugin for sending HTTP(s) requests on post-saves
	- Inspiration from https://github.com/wbond/sublime_prefixr

@author		Markus <markus@rwx.se>
@link		https://github.com/ettrig/sublime_markurl
@since		Version 1.0
'''

import os
import sys
import httplib
import string
import threading
import sublime
import sublime_plugin
from urlparse import urlparse

# Event listener
class MarkurlListener(sublime_plugin.EventListener):
	def on_post_save(self, view):
		view.run_command('markurl')

# Text-command
class MarkurlCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		threads = []
		enabled = bool(
			sublime.active_window().active_view().settings().get('markurl_enabled', False))
		url = sublime.active_window().active_view().settings().get('markurl_url', False)

		if not enabled or not url:
			return

		if self.valid8exts(self.view.file_name()):
			thread = Request(urlparse(url))
			threads.append(thread)
			thread.start()
			self.handle_threads(threads)

	# Handle multiple threads
	def handle_threads(self, threads, i=0, c=1):
		next_threads = []
		for thread in threads:
			if thread.is_alive():
				next_threads.append(thread)
				continue
			if thread.result == False:
				continue
			self.output(thread.result)
		threads = next_threads

		# Spinner
		if len(threads):
			before = i % 10
			after = (9) - before
			if not after:
				c = -1
			if not before:
				c = 1
			i += c
			self.view.set_status('markurl', 'Markurl [%s=%s]' % (' ' * before, ' ' * after))
			sublime.set_timeout(lambda: self.handle_threads(threads, i, c), 75)
			return

		self.view.erase_status('markurl')
		sublime.status_message('Markurl was successfull')

	# Output results
	def output(self, response):
		if "Error" in response:
			view = sublime.active_window().new_file()
			view.set_scratch(True)
			view.set_syntax_file('Packages/Regular Expressions/RegExp.tmLanguage')
			edit = view.begin_edit('markurl')
			view.insert(edit, 0, response)
			view.end_edit(edit)

	# Validate extensions for given file
	def valid8exts(self, filename, exts=["css", "js"]):
		filename, ext = os.path.splitext(filename)
		if not exts:
			return True
		for e in exts:
			if e in ext:
				return True
		return False
#eoc

# HTTP(s) request as thread
class Request(threading.Thread):

	def __init__(self, url_object, timeout=6):
		self.url_object = url_object
		self.timeout = timeout
		self.result = ""
		self.funcs = {
			'http':		httplib.HTTPConnection,
			'https':	httplib.HTTPSConnection
		}
		threading.Thread.__init__(self)

	def run(self):
		try:
		# If on linux i assume curl is installed...
			if sys.platform.startswith('linux'):
				status = 0
				result = ''
				response = os.popen('curl -fk -e "" -A Markurl -w "%{http_code}" ' + self.url_object.geturl())
				rows = response.readlines()
				if len(rows) > 0 and rows[-1] == '200':
					del rows[-1]
					for i in rows:
						result += i
					self.result = result
					return
				err = 'curl failed.'
			else:
				c = self.funcs[self.url_object.scheme](self.url_object.netloc, timeout=self.timeout)
				c.request('GET', self.url_object.path)
				response = c.getresponse()
				if response.status == 200:
					self.result = response.read()
					return
				err = '%s: http(s) response: %s %s' % (__name__, response.status, response.reason)

		except (httplib.HTTPException) as (e):
			err = '%s: error %s contacting %s.' % (__name__, str(e.code), self.url_object.netloc)
		except Exception as e:
			err = str(e)
		sublime.error_message("Markurl: " + err)
		self.result = False

#eoc