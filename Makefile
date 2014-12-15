export PYTHONPATH:=$(shell pwd)/wsgi/helpers

test:
	py.test-3 wsgi/kppvh/kppv_mod/kxhtml.py
	py.test-3 wsgi/helpers/sourcefile.py
	py.test-3 wsgi/kppvh/kppv_mod/points.py
