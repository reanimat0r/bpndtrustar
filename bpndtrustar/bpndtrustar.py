#!/usr/bin/env python3

import json
import sys
import os
import time
import datetime
from datetime import date
from random import randint
import calendar
import requests
import requests.auth
import argparse
import collections

from trustar import TruStar

IndicatorData = collections.namedtuple('IndicatorData', 'name type lastseen source enclaves notes tags')

def parse_date(str):
	parts = str.split("-")
	if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
		raise ValueError("Invalid date: {}".format(str))

	try:
		d = date(int(parts[0]), int(parts[1]), int(parts[2]))
	except:
		raise ValueError("Invalid date: {}".format(str))

	return d

def to_milliseconds(days):
    return days * 24 * 60 * 60 * 1000

def getTagIds(ts, enclaves):
	tagIds = {}
	allIndicatorTags = ts.get_all_indicator_tags(enclaves)
	if len(allIndicatorTags) == 0:
		return tagIds

	for indicatorTag in allIndicatorTags:
		if indicatorTag.name:
			tagIds[indicatorTag.name] = indicatorTag.id

	return tagIds

def getIndicatorEnrichment(ts, ioc):
	try:
		md = ts.get_indicator_metadata(ioc)
	except:
		return None

	indicator = md["indicator"]
	notes = {}
	for note in indicator.notes:
		tmp = json.loads(note)
		for key, value in tmp.items():
			notes[key] = value

	return IndicatorData(name=indicator.value,
						 type=indicator.type,
						 lastseen=time.strftime("%Y-%m-%d", time.gmtime(indicator.last_seen / 1000)),
						 source=indicator.source,
						 notes=notes,
						 tags=md["tags"],
						 enclaves=md["enclaveIds"])

# Takes a dictionary of name-value pairs. The names are displayed
# to the user and a list of selected values is returned.
# If any selection is 'q', then returns None
# If any selection is '0', then return [] to indicate that all was selected
# Ignores any blank entries (e.g. a,,b return [a,b]
def selectFromList(aDict, title):
	listSelections = []
	if len(aDict) == 0:
		return listSelections

	choices = sorted([name for name in aDict])
	choicesPerColumn = int(len(choices) / 2)

	print()
	print()
	for i in range(choicesPerColumn + 1):
		if i == 0:
			col1 = "0. All"
		else:
#			col1 = "{}. {}: {}".format(i, choices[i - 1], aDict[choices[i - 1]])
			col1 = "{}. {}".format(i, choices[i - 1])
		if i + choicesPerColumn < len(choices):
			col2 = "{}. {}".format(i + choicesPerColumn + 1, choices[i + choicesPerColumn])
#			col2 = "{}. {}: {}".format(i + choicesPerColumn + 1, choices[i + choicesPerColumn], aDict[choices[i + choicesPerColumn]])
		else:
			col2 = ""
		print("{:35} {:35}".format(col1, col2))

	print()

	while True:
		selections = input("Enter comma separated list of numbers (q to quit): ")
		selections = selections.replace(" ", ",")
		selections = selections.split(",")
		for selection in selections:
			if selection == "":
				continue
			if selection == 'q':
				return None
			if selection == "0":
				return []

			try:
				n = int(selection)
			except:
				print("Invalid selection: {}. Please try again".format(selection))
				listSelections = []
				break

			if n < 1 or n > len(choices):
				print("Invalid selection: {}, Please try again.".format(selection))
				listSelections = []
				break

			listSelections.append(aDict[choices[n - 1]])

		if len(listSelections) > 0:
			break

	return listSelections

def outputIOC(ts, enclaveNames, ioc, outputFile):
	data = getIndicatorEnrichment(ts, ioc)
	if data:
		print(str(data).replace('\n', ''))
		tags = ""
		if data.tags:
			tags = ";".join([tag.name for tag in data.tags])

		notesItems = {}
		for key, value in data.notes.items():
			if not key in notesItems:
				notesItems[key] = set()
			notesItems[key].add(value)

#			";".join(["{}:{}".format(key, value) for key, value in data.notes.items()])), file=outputFile)

#		print("{},{},{},{},{}".format(data.name,
#								data.type,
#								data.source,
#								tags,
#								";".join(["{}:{}".format(key, value) for key, value in notesItems.items()])), file=outputFile)
#								";".join([enclaveNames[enclaveId] for enclaveId in data.enclaves])))
#		print("Notes")
#		for key, value in data.notes.items():
#			print("{}: {}".format(key, value))
#		print()
	else:
		print('Indicator "{}" not found'.format(ioc))

def main():
	parser = argparse.ArgumentParser(description="Retrieve IOCs from TruSTAR and enrich them. Filter based on time range, enclave(s), and tag(s). Just use -r to retrieve IOCs submitted since midnight last night.")
	parser.add_argument("-r", "--retrieve", action="store_true", help="Retrieve IOCs based on the start/end dates, enclaves, and tags. Mutually exclusive with -i/--iocs.")
	parser.add_argument("-s", "--startdate", help="Starting date (YYYY-MM-DD) to search for IOCs. (default start of today)")
	parser.add_argument("-e", "--enddate", help="Ending date (YYYY-MM-DD) to search for IOCs (default end of today)")
	parser.add_argument("-n", "--enclaves", nargs="+", help="Space separated list of enclaves to search (default BCBS-Domain), '-n s' to select enclaves from a list of valid enclaves.")
	parser.add_argument("-t", "--tags", nargs="+", help="Space separated list of tags that IOCs must be tagged with, default is to return IOCs regardless of tags. '-t s' to select tags from a list of valid tags.")
	parser.add_argument("-i", "--iocs", nargs="+", help="Get enrichment data for IOCs. Specify a space separated list of IOCs. Mutually exclusive with -r/--retrieve.")
	parser.add_argument("-o", "--output", help="Filename of file where results are to be saved.")
	args = parser.parse_args()

	if not args.iocs and not args.retrieve:
		parser.error("Must specify either -r/--retrieve or -i/--iocs.")

	if args.iocs and (args.retrieve or args.startdate or args.enddate or args.enclaves or args.tags):
		parser.error("Ony IOC(s) can be specified when -i/--iocs is used. No other options are valid when -i/--iocs is specified.")

	if args.startdate:
		try:
			starttime = calendar.timegm(parse_date(args.startdate).timetuple()) * 1000
		except:
			parser.error("Invalid start date specified {}.".format(args.startdate))
	else:
		# The default start date is the earliest time today.
		# e.g. the start date on 2018-06-19 is 00:00:00 2018-06-19
		t = time.gmtime()
		starttime = calendar.timegm((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, t.tm_wday, t.tm_yday, t.tm_isdst)) * 1000

	if args.enddate:
		# Must add 1 to the date so that the end date is actually 00:00:00 on the next day.
		# This ensures getting all of the data on enddate.
		try:
			endtime = parse_date(args.enddate) + datetime.timedelta(days=1)
			endtime = calendar.timegm(endtime.timetuple()) * 1000
		except:
			parser.error("Invalid end date specified {}.".format(args.enddate))
	else:
		endtime = int(time.time()) * 1000

	ts = TruStar(config_role="trustar")
	enclaves = {}
	enclaveNames = {}
	for enclave in ts.get_user_enclaves():
		if enclave.read:
			enclaves[enclave.name] = enclave.id
			enclaveNames[enclave.id] = enclave.name

	enclaveSelections = []
	if args.enclaves:
		if 's' in args.enclaves:
			enclaveSelections = selectFromList(enclaves, "Enclaves")
			if enclaveSelections == None:
				sys.exit()
		else:
			for enclave in args.enclaves:
				if enclave in enclaves:
					enclaveSelections.append(enclaves[enclave])
				else:
					print("Invalid enclave: {}".format(enclave))
					sys.exit()

	tagIds = getTagIds(ts, enclaveSelections)

	tagSelections = []
	if args.tags:
		if 's' in args.tags:
			tagSelections = selectFromList(tagIds, "Tags")
			if tagSelections == None:
				sys.exit()
		else:
			for tag in args.tags:
				tagSelections.append(tagIds[tag])

	outputFile = sys.stdout
	if args.output:
		outputFile = open(args.output, "w")

	if args.iocs:
		for ioc in args.iocs:
			outputIOC(ts, enclaveNames, ioc, outputFile)
	else:
#		print("enclaves: {}".format(enclaveSelections), file=sys.stderr)
#		print("tags: {}".format(tagSelections), file=sys.stderr)
#		print(starttime)
#		print(endtime)
#		print(enclaveSelections)
#		print(tagSelections)
		indicators = ts.get_indicators(from_time=starttime, to_time=endtime, enclave_ids=enclaveSelections, included_tag_ids=tagSelections, page_size=500)
		for indicator in indicators:
			print("{},{}".format(indicator.value, indicator.type), file=outputFile)

	if args.output:
		outputFile.close()

if __name__ == '__main__':
    main()

