#!/usr/bin/env python3
import sys
import struct
import datetime
import os

import gpxpy
import gpxpy.gpx

quiet = True

class NavmiToGPX(object):
	def __init__(self, input_path, output_path):
		self.input_path = input_path
		self.output_path = output_path

		self.gpx = gpxpy.gpx.GPX()

		# Create first track in our GPX:
		self.gpx_track = gpxpy.gpx.GPXTrack()
		self.gpx.tracks.append(self.gpx_track)

		# Create first segment in our GPX track:
		self.gpx_segment = gpxpy.gpx.GPXTrackSegment()
		self.gpx_track.segments.append(self.gpx_segment)


	# DateTimes are stored in .NET Ticks

	@staticmethod
	def csharp_ticks_to_datetime(ticks):
		# From: https://gist.github.com/gamesbook/03d030b7b79370fb6b2a67163a8ac3b5
		"""Convert .NET ticks to datetime
		Args:
			ticks: integer
				i.e 100 nanosecond increments since 1/1/1 AD"""

		return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=ticks // 10)

	def parse0(self, f):
		timestamp, = struct.unpack("q", f.read(8))
		timestamp = self.csharp_ticks_to_datetime(timestamp)

		p, elevation, min_speed = None, None, None

		num1, = struct.unpack("d", f.read(8))
		if num1 != -200.0:
			num2, = struct.unpack("d", f.read(8))

			# num1 is lat, num2 is lon (see: NavmiLoader.cs)
			p = (num1, num2)

		num3, = struct.unpack("d", f.read(8))
		if num3 != -9999999.9:
			elevation = num3

		num4, = struct.unpack("d", f.read(8))
		if num4 != -1.0:
			min_speed = num4

		if not quiet:
			print(timestamp, p, elevation, min_speed)

		if timestamp and p and elevation:
			self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(
				latitude=p[0], longitude=p[1], elevation=elevation, time=timestamp))

	def parse1(self, f):
		"""Set Start Time"""
		timestamp, = struct.unpack("q", f.read(8))
		timestamp = self.csharp_ticks_to_datetime(timestamp)

		if not quiet:
			print("Started", timestamp)

	def parse2(self, f):
		"""Pause"""
		timestamp, = struct.unpack("q", f.read(8))
		timestamp = self.csharp_ticks_to_datetime(timestamp)

		if not quiet:
			print("Paused", timestamp)

	def parse3(self, f):
		"""Resume"""
		timestamp, = struct.unpack("q", f.read(8))
		timestamp = self.csharp_ticks_to_datetime(timestamp)

		if not quiet:
			print("Resumed", timestamp)

	def parse4(self, f):
		"""Lap"""
		timestamp, = struct.unpack("q", f.read(8))
		timestamp = self.csharp_ticks_to_datetime(timestamp)

		if not quiet:
			print("Lap", timestamp)

	record_pasers = {
		b'\x00': parse0,
		b'\x01': parse1,
		b'\x02': parse2,
		b'\x03': parse3,
		b'\x04': parse4,
	}

	def run(self):
		with open(self.input_path, "rb") as f:
			navmi = f.read(5)
			if navmi != b"NAVMI":
				raise RuntimeError("Not a NAVMI binary file")

			b = f.read(1)
			if b != b'\x01':
				raise RuntimeError("Bad byte")

			while True:
				b = f.read(1)

				if b == b'':
					break

				self.record_pasers[b](self, f)

		with open(self.output_path, "w") as outf:
			print(self.gpx.to_xml(), file=outf)

		print("Written to {}".format(output_path))

if __name__ == "__main__":
	files = sys.argv[1:]

	for input_path in files:
		output_path = os.path.splitext(input_path)[0] + ".gpx"

		NavmiToGPX(input_path, output_path).run()
