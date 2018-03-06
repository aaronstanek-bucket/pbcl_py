class pbcl_line:
    pass

class script_reader:
    def reset(self):
        self.loc = dict()
        self.glob = dict()
        self.pickup = 0
        self.term = False
    def load_script(self,scr):
        self.reset()
        self.script = scr
    def forward(self):
        self.loc = dict()
        spot = self.pickup
        while True:
            if spot>=len(self.script):
                self.pickup = len(self.script)
                self.term = True
                return
            g = self.script[spot]
            if g.command==".":
                self.loc[g.varname] = g.varvalue
                spot += 1
            elif g.command=="$":
                self.glob[g.varname] = g.varvalue
                spot += 1
            elif g.command=="%":
                if g.varname in self.glob:
                    del(self.glob[g.varname])
                spot += 1
            elif g.command=="#":
                self.pickup = spot+1
                return
            else:
                raise Exception()
    def here(self):
        g = self.script[self.pickup-1]
        return g.directive
    def get_var(self,vn):
        if vn in self.loc:
            return self.loc[vn]
        if vn in self.glob:
            return self.glob[vn]
        return ""
    def var_exists(self,vn):
        if vn in self.loc:
            return True
        if vn in self.glob:
            return True
        return False

def string_encode(s):
    # converts a string into a list of ascii values
    # safely omits characters outside the standard
    h = s.encode("UTF-8")
    ou = []
    for x in h:
        if x>=32:
            if x!=127:
                ou.append(x)
        elif x==10:
            ou.append(x)
        elif x==9:
            ou.append(x)
    return ou

def filter_bytes(h):
    ou = []
    for x in h:
        if x>=32:
            if x!=127:
                ou.append(x)
        elif x==10:
            ou.append(x)
        elif x==9:
            ou.append(x)
    return ou

def break_into_lines(d):
    # takes a list of ascii values and breaks it by lines
    # keeps all empty lines
    # returns list(list(ascii values))
    ou = []
    k = []
    for x in d:
        if x==10:
            ou.append(k)
            k = []
        else:
            k.append(x)
    if len(k)!=0:
        ou.append(k)
    return ou

def chopped_string(b):
    # takes list(ascii values)
    # returns string
    # turns a list of ascii values into a string, removing leading and trailing spaces and tabs
    s = 0
    while True:
        if b[s]!=32 and b[s]!=9:
            break
        s += 1
    f = len(b)-1
    while True:
        if b[f]!=32 and b[f]!=9:
            break
        f -= 1
    return bytes(b[s:f+1]).decode("UTF-8")

def is_valid_hex_char(c):
    # takes an ascii value
    # returns bool
    # detemines is character is a valid character in a hex number
    if c>=48 and c<=57:
        return True
    if c>=65 and c<=70:
        return True
    return False

def decode_hex_number(c):
    # takes a single ascii value, (0-9,A-F)
    # returns the hex value associated with that character (0-15)
    # input must be in domain of this function, functions does not check domain
    if c<58:
        return c-48
    return c-55

def decode_escape_sequence(s):
    # takes a list(ascii values)
    # returns an ascii value of the encoded character
    # returns the length of the escape sequence
    # s may be 1 or 2 bytes long
    # if it is 1 byte, we expect:
    #   s, t, n, z : (space, tab, return, backslash)
    # if it is 2 bytes, it may hold any valid hex value
    k = [] # k is uppercase only version of input
    for x in s:
        if x>96:
            k.append(x-32)
        else:
            k.append(x)
    if len(k)==0:
        raise Exception("Invalid Escape Sequence")
    if k[0]==83: # S
        return [32,1]
    if k[0]==84: # T
        return [9,1]
    if k[0]==78: # N
        return [10,1]
    if k[0]==90: # Z
        return [92,1] # \
    # it is not a valid one byte sequence
    if is_valid_hex_char(k[0])==False:
        raise Exception("Invalid Escape Sequence")
    if is_valid_hex_char(k[1])==False:
        raise Exception("Invalid Escape Sequence")
    # now this must be a valid hex number
    ou = (decode_hex_number(k[0])*16) + decode_hex_number(k[1])
    return [ou,2]

def resolve_escape_sequences(b):
    # takes list(ascii values)
    # returns list(ascii values)
    # converts all escape sequences to their true forms
    ou = []
    i = 0
    while True:
        if i>=len(b):
            break
        x = b[i]
        if x!=92: # \
            ou.append(x)
            i += 1
        else:
            # we have an escape sequence
            es = decode_escape_sequence(b[i+1:i+3]) # we don't know if it is one byte or two byte long
            ou.append(es[0])
            i += es[1]+1
    return ou

def can_ignore_line(b):
    # takes list(ascii values)
    # returns bool
    # determines if line is empty, or has a comment
    if len(b)==0:
        return True
    if b[0]==47: # /
        return True
    return False

def decode_var(b):
    # takes list(ascci values)
    # returns pbcl_line
    ou = pbcl_line()
    if b[0]==46: # .
        ou.command = "."
    else:
        ou.command = "$"
    i = 0
    while b[i]!=61 and b[i]!=38: # = &
        i += 1
    ou.varname = chopped_string(b[1:i])
    if b[i]==61: # =
        ou.varvalue = chopped_string(b[i+1:])
    else:
        ou.varvalue = chopped_string(resolve_escape_sequences(b[i+1:]))
    return ou

def decode_not_var(b):
    # takes list(ascii values)
    # returns pbcl_line
    ou = pbcl_line()
    if b[0]==35:
        ou.command = "#"
        ou.directive = chopped_string(b[1:])
    else:
        ou.command = "%"
        ou.varname = chopped_string(b[1:])
    return ou

def make_objects(b):
    # takes list(list(ascii values))
    # returns list(pbcl_line)
    ou = []
    for ln_num in range(len(b)):
        ln = b[ln_num]
        try:
            if can_ignore_line(ln):
                pass
            elif ln[0]==46 or ln[0]==36: # . $
                ou.append(decode_var(ln))
            elif ln[0]==35 or ln[0]==37: # # %
                ou.append(decode_not_var(ln))
            else:
                raise Exception()
        except:
            raise Exception("PBCL syntax error. Line: "+str(ln_num+1))
    return ou

def load(filename):
    infile = open(filename,"rb")
    s = infile.read()
    infile.close()
    s = filter_bytes(s)
    s = break_into_lines(s)
    s = make_objects(s)
    ou = script_reader()
    ou.load_script(s)
    return ou
