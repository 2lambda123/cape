#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CAPE modules
import cape.attdb.rdb as rdb

# Read DataKit from MAT file
db = rdb.DataKit("CN-alpha-beta.mat", WriteFormats={"alpha": "%5.2f"})

# Write simple dense CSV file
db.write_csv("CN-default.csv")

