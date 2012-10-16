TARBALL_DIR=.

tarball:
	git archive master | bzip2 > zeus-server_`git describe --abbrev=0`.tar.bz2
