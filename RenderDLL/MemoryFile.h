#ifndef _MEMORY_FILE_H_
#define _MEMORY_FILE_H_

//MemoryFile
//Maps a file to memory
class MemoryFile {
	int size;
	unsigned char* data;
public:
	//Create a memory file object from the file 'filename'
	MemoryFile(const char* filename, bool suppressErrors=false);
	~MemoryFile();

	//returns a pointer to the memory-mapped file.
	//returns NULL if the file could not be opened
	const unsigned char* getPtr() const;
	
	//returns the size of the memory-mapped file.
	//returns 0 if the file could not be opened
	int getSize() const;
};

#endif