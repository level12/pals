objects = $(wildcard *.in)
outputs := $(objects:.in=.txt)


.PHONY: all check clean

all: $(outputs)

%.txt: %.in
	pip-compile -v --output-file $@ $<

# Dependency chain
dev.txt: common.txt
