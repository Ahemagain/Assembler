import re
import struct

# parser class for assembler
# bit of a misnomer in naming really
# public:
#	jump_table ( list)
#	run ( method)
#	get_addresses (method)
#	parse (method)
class Parser:

	#constructor, takes file pointer of input file
	def __init__(self, input):

		self. input = input
		self.jump_table = {}

		#mapping of opcode token to its handler, and its possible machine representations
		#reresentations are immediate form, register form, and indirect address form
		self._instruction_map = {	"add":	(self._ternary_handler, "\x81", "\x82", "\x83"),
									"sub":	(self._ternary_handler, "\x84", "\x85", "\x86"),
									"mul":	(self._ternary_handler, "\x87", "\x88", "\x89"),
									"div":	(self._ternary_handler, "\x8A", "\x8B", "\x8C"),
									"and":	(self._ternary_handler, "\x8D", "\x8E", "\x8F"),
									"or":	(self._ternary_handler, "\x90", "\x91", "\x92"),
									"xor":	(self._ternary_handler, "\x93", "\x94", "\x95"),
									"not":	(self._ternary_handler, "\x00", "\x96", "\x00"),
									"ld":	(self._binary_handler,	"\x97", "\x00", "\x98"),
									"st":	(self._binary_handler,  "\x99", "\x00", "\x9A"),
									"mov":	(self._binary_handler,  "\x9B", "\x9C", "\x00"),
									"cmp":	(self._unary_handler,   "\x9D", "\x00", "\x9E"),
									"jmp":	(self._unary_handler,   "\x9F", "\x00", "\xA0")}

		#register map, maps register name to machine code address
		self._register_map = {		"r0"  :"\x00",
									"r1"  :"\x01",
									"r2"  :"\x02",
									"r3"  :"\x03",
									"r4"  :"\x04",
									"r5"  :"\x05",
									"r6"  :"\x06",
									"r7"  :"\x07",
									"ra1" :"\x08",
									"ra2" :"\x09",
									"ra1l":"\x0A",
									"ra1h":"\x0B",
									"ra2l":"\x0C",
									"ra2h":"\x0D"}							
	#assemble, takes output file pointer 
	def run(self, out_fp):
		self.get_addresses()
		self.parse(out_fp)

	# step 1, extract the lables and calculate their address
	# currently assumes all instructions use 4 bytes, 
	# this is not the most efficient, and will probably get changed in the future
	def get_addresses(self):
		byte_counter = 0

		for line in self.input:
			m=re.match("(.*):",line)
			if(m):
				self.jump_table[m.group(1)] = byte_counter
			else:
				byte_counter += 4 ##temporary magic...

		#reset input file pointer to beginning.
		#by doing this, we need not copy the whole file to memory,
		# and can just iterate through in both steps
		self.input.seek(0)

	# the parse step, takes the file pointer of the output file
	# requires an assembled jump table from get_addresses
	# due to the aformentioned "hack" each instruction is padded to 4 bytes
	def parse(self, output):
		line_count = 1
		for line in self.input:

			#ignore labels
			if not (re.match("(.*):",line)):

				#remove tabs and newlines
				line = re.sub('\t|\n','',line)

				#split to tokens
				tokens = re.split(' |, |,|',line)

				try:
					# take opcode, find it in the map, and call the handler
					out = self._instruction_map[tokens[0]][0](tokens)
				except ParseError as error:
					print "Parse Error: Line ",line_count," Message: ",error.msg
					return
				except:
					print "Unexpected Error: Line ",line_count

				#write the instruction
				output.write(out)

			line_count+=1
			
	# handles instructions with arity of 3.
	# takes tokenised instruction, returns binary string.
	def _ternary_handler(self, tokens):

		det_token = tokens[3]
		det_char = det_token[0]

		byte = [None]*4

		#determine variation of instruction and operate on it
		#immediate handling
		if(det_char is '#'):
			byte[0] = self._instruction_map[tokens[0]][1]

			(byte[2],byte[3]) = self._immediate_handler(det_token,16)

		#register handling
		elif(det_char is 'r'):
			byte[0] = self._instruction_map[tokens[0]][2]
			op3 = self._register_handler(det_token)
			byte[2] = self._nibbles_to_byte(op3,"\x00")
			byte[3]= "\x00"

		#indirect handling
		elif(det_char is '['):
			byte[0] = self._instruction_map[tokens[0]][3]

			(ar,o4) = self._indirect_handler(tokens[3:],4)
			byte[2] = self._nibbles_to_byte(ar,o4)
			byte[3] = "\x00"

		else:
			raise ParseError("Malformed Syntax")

		op1 = self._register_handler(tokens[1])

		op2 = self._register_handler(tokens[2])

		byte[1] = self._nibbles_to_byte(op1,op2)

		return bytearray("".join(byte))

	# instructions with arity 2. takes tokenised instruction.
	def _binary_handler(self,tokens):
		det_token = tokens[2]
		det_char = det_token[0]

		byte = [None]*4
		op1 = self._register_handler(tokens[1])

		if(det_char is '#'):
			byte[0] = self._instruction_map[tokens[0]][1]
			byte[1] = self._nibbles_to_byte(op1,"\x00")

			(byte[2],byte[3]) = self._immediate_handler(det_token,16)

		elif(det_char is 'r'):
			byte[0] = self._instruction_map[tokens[0]][2]
			op2 = self._register_handler(det_token)

			byte[1] = self._nibbles_to_byte(op1,op2)
			byte[2] = "\x00"
			byte[3] = "\x00"

		elif(det_char is '['):
			byte[0] = self._instruction_map[tokens[0]][3]

			(ar,(byte[2],byte[3])) = self._indirect_handler(tokens[2:],16)
			byte[1] = self._nibbles_to_byte(op1,ar)

		else:
			raise ParseError("Malformed Syntax")

		return bytearray("".join(byte))

	#arity 1 handler
	def _unary_handler(self,tokens):
		det_token = tokens[1]
		det_char = det_token[0]

		byte = [None]*4

		if(det_char is '#'):
			byte[0] = self._instruction_map[tokens[0]][1]
			(byte[1],byte[2]) = self._immediate_handler(det_token,16)
			byte[3]="\x00"


		elif(det_char is '['):
			byte[0] = self._instruction_map[tokens[0]][3]
			(ar,imm) = self._indirect_handler(tokens[1:],4)
			byte[1] = self._nibbles_to_byte(ar,imm)
			(byte[2],byte[3]) = ("\x00","\x00")

		else:
			# handles label to immediate convertion
			address = self._label_handler(det_token)
			if address is not None:
				byte[0]= self._instruction_map[tokens[0]][1]
				(byte[1],byte[2]) = address
				byte[3]="\x00"
			else:
				raise ParseError("Malformed Syntax")

		return bytearray("".join(byte))

	#handles immediates
	def _immediate_handler(self,imm, size):
		if (imm[0] is '#'):
			value = int(imm[1:])
			if size <= 8:
				return struct.pack('B',value)
			elif size <= 16:
				#bitshifiting to divide the python int into two 8 bit ints.
				v1 = value >> 8
				v2 = value & 0xFF

				return (struct.pack('B',v1),struct.pack('B',v2))

		raise ParseError("Bad Immediate")

	# handles registers, simple wrapper around dictionary.
	def _register_handler(self,reg):
		if reg in self._register_map:
			return self._register_map[reg]
		else:
			raise ParseError("Bad Register")

	# handles indirect addressing. takes the 2 tokens corresponding to this, and the max size of the immediate.
	def _indirect_handler(self,tokens, imm_size):
		if (tokens[0][0] is "[") and (tokens[1][-1] is "]"):
			return (self._register_handler(tokens[0][1:]), self._immediate_handler(tokens[1][:-1],imm_size))
		else:
			raise ParseError("Faulty Indirect Address") 

	#converts lables into intermediate format.
	def _label_handler(self, label):
		if label in self.jump_table:
			address = self.jump_table[label]

			return(struct.pack('B',address >> 8), struct.pack('B',address & 0xFF))
		else:
			raise ParseError("Unrecognised Label")

	#takes 2 4 bit nibbles(stored in 8 bit), and combines them to one 8 bit value
	#commonly used to place 2 register adresses in 8 bits, solves python representation issues,
	# and keeps the assembler operating a byte at a time.
	def _nibbles_to_byte(self,n1,n2):
		a = int(n1.encode('hex'),16)
		b = int(n2.encode('hex'),16)
		a = a << 4
		return struct.pack('B',a+b)


#generic error class, implemented for best practice
class Error(Exception):
    pass
#class innherits packages default error class, deals with parse errors.
class ParseError(Error):
	def __init__(self, msg):
		self.msg = msg




