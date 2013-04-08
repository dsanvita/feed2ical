#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from datetime import datetime, timedelta
import os
import feedparser
import html2text
import logging
import re
from urllib import quote_plus
from xml.dom import minidom

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api.urlfetch import fetch

class MainHandler(webapp.RequestHandler):
	def get(self):
		template_values = { 'host':self.request.headers.get('host', 'no host') }
		path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
		self.response.out.write(template.render(path, template_values))

class Convert(webapp.RequestHandler):
	def get(self):
		url = self.request.get('url')
		try:
			logging.info(url)
			result = fetch(url, headers = {'Cache-Control' : 'max-age=300'})
			if result.status_code == 200:
				sContent = result.content
				sContent = re.sub(r'(<|</)([a-zA-Z]+):start(time|date)>', r'\1dcterms:created>', sContent)
				sContent = re.sub(r'(<|</)([a-zA-Z]+):end(time|date)>', r'\1expirationDate>', sContent)
				d = feedparser.parse(sContent)
				try:
					d.feed.title_text = re.sub(r'\s+', " ", html2text.html2text(d.feed.title))
					d.feed.description_text = re.sub(r'\s+', " ", html2text.html2text(d.feed.description))
				except:
					pass
				allday = True
				for entry in d.entries:
					try:
						datPubDate = datetime(*(entry.updated_parsed[0:6]))
					except:
						datPubDate = datetime.utcnow()
					try:
						if (datPubDate.hour + datPubDate.minute + datPubDate.second) > 0:
							allday = False
							break
					except:
						pass
				for entry in d.entries:
					entry.title_text = re.sub(r'\s+', " ", html2text.html2text(entry.title))
					try:
						entry.description_text = html2text.html2text(entry.description)
						entry.description_text = re.sub(r'[ ]*\n+[ ]*', "\N", entry.description_text)
						entry.description_text = re.sub(r';', "\;", entry.description_text)
						entry.description_text = re.sub(r',', "\,", entry.description_text)
						entry.description_text = re.sub(r'[ \t\r]+', " ", entry.description_text)
					except:
						pass
					try:
						try:
							datPubDate = datetime(*(entry.updated_parsed[0:6]))
						except:
							datPubDate = datetime.utcnow()
						try:
							datStartDate = datetime(*(entry.created_parsed[0:6]))
						except:
							datStartDate = datPubDate
						try:
							datEndDate = datetime(*(entry.expired_parsed[0:6]))
						except:
							if allday:
								datEndDate = (datPubDate + timedelta(days=1))
							else:
								datEndDate = (datPubDate + timedelta(hours=1))						

						if allday:
							stfmt = "%Y%m%d"
						else:
							stfmt = "%Y%m%dT%H%M%SZ"
						entry.start_ical = datStartDate.strftime(stfmt)
						entry.end_ical = datEndDate.strftime(stfmt)						
					except:
						pass
				template_values = { 'd':d }
				path = os.path.join(os.path.dirname(__file__), 'templates/convert.html')
				self.response.headers['Content-Type'] = "text/plain"
				self.response.out.write(template.render(path, template_values))
			else:
				self.response.out.write("Error " + str(result.status_code) + " when retrieving feed.")
		except:
			self.response.out.write("Error downloading feed.")
			logging.info("Error downloading feed url")
			raise

class Opml(webapp.RequestHandler):
	def post(self):
		try:
			opml = self.request.get('opmlfile')
			mydom = minidom.parseString(opml)
			opml_title = mydom.getElementsByTagName("title")[0].firstChild.data
			opml_items = mydom.getElementsByTagName("outline")
			
			channels = []
			for item in opml_items:
				item_text = item.getAttribute("text")
				item_htmlurl = item.getAttribute("htmlUrl")
				item_xmlurl = item.getAttribute("xmlUrl")
				channels.append({'text':item_text, 'htmlurl':item_htmlurl, 'xmlurl':quote_plus(item_xmlurl)})
			
			template_values = { 'opml_title':opml_title, 'channels':channels, 'host':self.request.headers.get('host', 'no host') }
			path = os.path.join(os.path.dirname(__file__), 'templates/opml.html')
			self.response.out.write(template.render(path, template_values))
		except:
			self.response.out.write("Error processing opml file.")

		
application = webapp.WSGIApplication([
  ('/', MainHandler),
  ('/convert', Convert),
  ('/opml', Opml)
], debug=True)

def main():
	util.run_wsgi_app(application)

if __name__ == '__main__':
	main()
