#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyCart
import cape.test
import os, shutil


# Get control interface
cntl = pyCart.Cart3d()

# Read the databook
cntl.ReadDataBook()

# Get the value
CA = cntl.DataBook['bullet_no_base']['CA'][0]

# STDOUT
print("CA = %0.3f" % CA)

