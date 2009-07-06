#include "MemoryFile.h"
#include <fstream>
#include <iostream>

using namespace std;

MemoryFile::MemoryFile(const char* filename, bool suppressErrors) : size(0), data(NULL) {
	ifstream infile(filename, ios::binary);
	if(infile.good()) {
		infile.seekg(0, ios::end);
		size = infile.tellg();
		infile.seekg(0, ios::beg);
		data = new unsigned char[size];
		infile.read((char*)data, size);
		infile.close();
	} else {
		data = NULL;
		size = 0;
		if(!suppressErrors) {
			cerr << "Unable to open file '" << filename << "'" << endl;
		}
	}
}

MemoryFile::~MemoryFile() {
	delete[] data;
}

const unsigned char* MemoryFile::getPtr() const {
	return data;
}

int MemoryFile::getSize() const {
	return size;
} 