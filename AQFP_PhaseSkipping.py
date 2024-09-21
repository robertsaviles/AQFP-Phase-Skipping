import random
#Graph Node Class Definitions
class Node:
    def __init__(self,name,gate_type,inputs,inversions):
        self.name = name
        self.gate_type = gate_type
        self.inputs = inputs
        self.inversions=inversions
        self.fanouts = []
        self.ASAP = 0
        self.freeze_ASAP=0
        self.ALAP = 0
        self.slack = 0
        self.depth = 0
        self.depth_id = 0
        self.splitter_in = []
        self.splitter_out =[]
        self.Find_ASAP()
        self.phases = 4
        for i in inputs:
            self.splitter_in.append(0)
        self.updateFanouts()
    def __str__(self):
        clk = self.depth%self.phases
        if (clk==0):
            clk=self.phases
        line = self.gate_type+"_AQFP "+self.name+"_"+"( clk_"+str(clk)+" , "
        for i in self.inputs:
            line += i.name + " , "
        for inv in self.inversions:
            line += str(inv)+ " , "
        line+=self.name+" );\n"
        return line
    def Find_Slack(self,phases):
        if (self.gate_type =="maj3" or self.gate_type =="PO" or self.gate_type=="PI"):
            self.slack=0
        elif (len(self.fanouts)==1):
            self.slack = self.fanouts[0].depth - self.depth - phases
            #print(self.fanouts[0].name + ":"+str(self.fanouts[0].depth)+"  "+self.name+":"+str(self.depth))
        elif (len(self.splitter_out)==1):
            self.slack = self.splitter_out[0].depth - self.depth -phases
            #print(self.splitter_out[0].name + ":"+str(self.splitter_out[0].depth)+"  "+self.name+":"+str(self.depth))
    def Find_ASAP(self):
        if (len(self.inputs)==0):
            self.ASAP=1
        elif(self.freeze_ASAP==0):
            temp=1
            for i in self.inputs:
                if (i.ASAP+1>temp):
                    temp = i.ASAP+1
            self.ASAP=temp
    def Find_ALAP(self):
        if (len(self.fanouts)==0 or len(self.inputs)==0):
            self.ALAP=self.ASAP
        else:
            temp = 999999
            for o in self.fanouts:
                if (o.ALAP-1<temp):
                    temp = o.ALAP-1
            self.ALAP = temp
    def addFanout(self,fanout):
        self.fanouts.append(fanout)
    def connect_splitter(self,fanouts,root):
        for f in fanouts:
            f.add_splitter(root,self)
            self.addFanout(f)
    def updateFanouts(self):
        if (self.gate_type=="splitter"):
            self.inputs[0].splitter_out.append(self)
            if(self.inputs[0].gate_type == "splitter"):
                self.splitter_in = self.inputs
                self.inputs[0].fanouts.append(self)
                #self.inputs = []
        else:
            for i in self.inputs:
                i.addFanout(self)
    def reset_splitters(self):
        self.splitter_out =[]
        for f in self.fanouts:
            index = 0
            count = -1
            for i in f.inputs:
                count+=1
                if (i.name == self.name):
                    index = count
            f.splitter_in[index] = 0
    def add_splitter(self,root,splitter):
        index = 0
        count = -1
        for i in self.inputs:
            count+=1
            if (i.name == root.name):
                index = count
        self.splitter_in[index] = splitter
    def insertbuf(self,driver,buf):
        index = -1
        for s in self.inputs:
            index+=1
            if (s.name==driver.name):
                self.inputs[index]=buf
    def clean_connections(self):
        index =-1
        for i in self.inputs:
            index+=1
            if (self.splitter_in[index]==0):
                continue
            else:
                self.inputs[index]=self.splitter_in[index]
        #remove all inputs that are indirect, replace them with a splitter input if one exists
            

class Ntk:
    def __init__(self,name):
        self.name = name
        self.dict = {}
        self.netlist = []
        self.splitters = []
        self.s_dict = {}
        self.phases=8
        self.POs = []
        self.PIs = []
        self.wires = []
    def set_phases(self):
        for n in self.netlist:
            n.phases = self.phases
        for s in self.splitters:
            s.phases = self.phases
    def add(self,node):
        self.netlist.append(node)
        self.dict[node.name]=len(self.netlist)-1
        if (node.gate_type != "PO" and node.gate_type != "PI"):
            self.wires.append(node.name)
    def add_splitter(self,splitter):
        self.splitters.append(splitter)
        self.s_dict[splitter.name]=len(self.splitters)-1
    def Obj(self,ID):
        return self.netlist[self.dict[ID]]
    def Set_ALAP(self):
        for n in reversed(self.netlist):
            n.Find_ALAP()
    def Fix_outputs(self):
        depth = 0
        for n in self.netlist:
            if (n.gate_type=="PO"):
                if (depth<n.ASAP):
                    depth = n.ASAP
        for n in self.netlist:
            if (n.gate_type=="PO"):
                n.ASAP = depth
                n.ALAP = depth
    def parse(self,filename):
        file = open(filename,'r')
        lines = file.readlines()
        for line in lines:
            entry = line.split()
            if (entry[0]=="module"):
                self.name = entry[1].split("(")[0]
            elif (entry[0]=="input"):
                for PI in entry:
                    if (PI!="input" and PI!="," and PI!=";"):
                        temp = Node(PI,"PI",[],[])
                        self.add(temp)
                        self.PIs.append(PI)
            elif (entry[0]=="assign"):
                node_name = entry[1]
                if (entry[3]=="("):
                    temp = entry[4].split("~")
                    in1 = temp[-1]
                    inv1 = len(temp)-1
                    temp = entry[6].split("~")
                    in2 = temp[-1]
                    inv2 = len(temp)-1
                    temp = entry[12].split("~")
                    in3 = temp[-1]
                    inv3 = len(temp)-1
                    #print(str(in1) + " " + str(in2) + " " +str(in3))
                    new = Node(node_name,"maj3",[self.Obj(in1),self.Obj(in2),self.Obj(in3)],[inv1,inv2,inv3])
                    self.add(new)
                    new.splitter_in = [0,0,0]
                elif(entry[4]=="&"):
                    temp = entry[3].split("~")
                    in1 = temp[-1]
                    inv1 = len(temp)-1
                    temp = entry[5].split("~")
                    in2 = temp[-1]
                    inv2 = len(temp)-1
                    new = Node(node_name,"and",[self.Obj(in1),self.Obj(in2)],[inv1,inv2])
                    self.add(new)
                    new.splitter_in = [0,0]
                elif(entry[4]=="|"):
                    temp = entry[3].split("~")
                    in1 = temp[-1]
                    inv1 = len(temp)-1
                    temp = entry[5].split("~")
                    in2 = temp[-1]
                    inv2 = len(temp)-1
                    new = Node(node_name,"or",[self.Obj(in1),self.Obj(in2)],[inv1,inv2])
                    self.add(new)
                    new.splitter_in = [0,0]
                else:
                    PO = entry[1]
                    temp = entry[3].split("~")
                    in1 = temp[-1]
                    inv1 = len(temp)-1
                    new = Node(PO,"PO",[self.Obj(in1)],[inv1])
                    self.add(new)
                    new.splitter_in = [0]
                    self.POs.append(PO)
        file.close()
    def deleteSplitters(self):
        for s in self.splitters:
            del s
        self.s_dict = {}
        self.splitters=[]
        for n in self.netlist:
            n.reset_splitters()
    def deleteTree(self,splitter_root):
        for s in splitter_root.splitter_out:
            self.deleteTree(s)
        self.splitters.pop(self.s_dict[splitter_root.name])
        print("Removing "+splitter_root.name)
        del self.s_dict[splitter_root.name]
        del splitter_root
        #remove from list
        #remove from dict
        #del object
    def Print_depths(self):
        for n in self.netlist:
            print(n.name + " : " +str(n.depth))
        for s in self.splitters:
            print(s.name + ": " + str(s.depth))
    def CleanNtk(self):
        for g in self.netlist:
            g.clean_connections()
        for s in self.splitters:
            s.clean_connections()
    def verify(self,pr):
        buf = 0
        splits=0
        for n in self.netlist:
            if (n.gate_type=="buf"):
                buf+=1
            for i in n.inputs:
                if (n.depth>i.depth+pr):
                    print("ERROR:Netlist Check Failed on connection ("+i.name+","+str(i.depth)+") -> ("+n.name+","+str(n.depth)+")")
                    return False
        for s in self.splitters:
            splits+=1
            for i in n.inputs:
                if (n.depth>i.depth+pr):
                    print("ERROR:Netlist Check Failed on connection ("+i.name+","+str(i.depth)+") -> ("+n.name+","+str(n.depth)+")")
                    return False
        print("Network is Appropriately Balanced\nRecovered Inserted Cost:"+str(buf+splits)+"\nBuffers = "+str(buf)+"\nSplitters = "+str(splits))
        return True
        
import os
import math
import numpy

def Formulate_CPLEX(ntk,N):
    obj_function=[]
    #bounds = ["Bounds\n"]
    with open('temp.txt','w') as temp:
        temp.write("Subject To\n")
        for n in ntk.netlist:
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=1\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"-D_outputs = 0\n")
            else:
                if (len(n.splitter_out)==1):
                    objfun="C_"+n.name+"_"+n.splitter_out[0].name
                    obj_function.append(objfun)
                    line = objfun + ">=0\n"
                    temp.write(line)
                    line = "D_"+n.splitter_out[0].name+" - D_"+n.name+">=1\n" 
                    temp.write(line)
                    line = "D_"+n.splitter_out[0].name+" - D_"+n.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+"\n"
                    temp.write(line)
                else:
                    if (len(n.fanouts)==0):
                        lined = 1
                    else:
                        objfun="C_"+n.name+"_"+n.fanouts[0].name
                        obj_function.append(objfun)
                        line = objfun + ">=0\n"
                        temp.write(line)
                        line = "D_"+n.fanouts[0].name+" - D_"+n.name+">=1\n"
                        temp.write(line)
                        line = "D_"+n.fanouts[0].name+" - D_"+n.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+"\n"
                        temp.write(line)
        for s in ntk.splitters:
            for g in s.fanouts:
                if(g.gate_type!="splitter"):
                    objfun="C_"+s.name+"_"+g.name
                    obj_function.append(objfun)
                    line = objfun + ">=0\n"
                    temp.write(line)
                    line = "D_"+g.name+" - D_"+s.name+">=1\n"
                    temp.write(line)
                    line = "D_"+g.name+" - D_"+s.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+"\n"
                    temp.write(line)
            for sp in s.splitter_out:
                objfun="C_"+s.name+"_"+sp.name
                obj_function.append(objfun)
                line = objfun + ">=0\n"
                temp.write(line)
                line = "D_"+sp.name+" - D_"+s.name+">=1\n" 
                temp.write(line)
                line = "D_"+sp.name+" - D_"+s.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+"\n"
                temp.write(line)
    filename = "problem.lp" #ntk.name+"_"+str(N)+".lp"
    #sol_file = "problem_sol.txt" #ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Minimize\n"
        for o in obj_function:
            objective += o + " + "
        objective += "XNULL;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
        lp.write("end")
    ti = time.time()
    os.system("./solve > junk.txt")
    return (time.time()-ti)
def Formulate(ntk,N):
    obj_function=[]
    with open('temp.txt','w') as temp:
        for n in ntk.netlist:
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=1;\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"=D_outputs;\n")
            else:
                if (len(n.splitter_out)==1):
                    objfun="C_"+n.name+"_"+n.splitter_out[0].name
                    obj_function.append(objfun)
                    line = "1<="+"D_"+n.splitter_out[0].name+" - D_"+n.name+";\n" 
                    temp.write(line)
                    line = "D_"+n.splitter_out[0].name+" - D_"+n.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+";\n"
                    temp.write(line)
                else:
                    if (len(n.fanouts)==0):
                        lined = 1
                    else:
                        objfun="C_"+n.name+"_"+n.fanouts[0].name
                        obj_function.append(objfun)
                        line = "1<="+"D_"+n.fanouts[0].name+" - D_"+n.name+";\n"
                        temp.write(line)
                        line = "D_"+n.fanouts[0].name+" - D_"+n.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+";\n"
                        temp.write(line)
        for s in ntk.splitters:
            for g in s.fanouts:
                if(g.gate_type!="splitter"):
                    objfun="C_"+s.name+"_"+g.name
                    obj_function.append(objfun)
                    line = "1<="+"D_"+g.name+" - D_"+s.name+";\n"
                    temp.write(line)
                    line = "D_"+g.name+" - D_"+s.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+";\n"
                    temp.write(line)
            for sp in s.splitter_out:
                objfun="C_"+s.name+"_"+sp.name
                obj_function.append(objfun)
                line = "1<="+"D_"+sp.name+" - D_"+s.name+";\n" 
                temp.write(line)
                line = "D_"+sp.name+" - D_"+s.name+ "- "+str(N)+" "+objfun+" <= "+ str(N)+";\n"
                temp.write(line)
    filename = ntk.name+"_"+str(N)+".lp"
    sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Min: "
        for o in obj_function:
            objective += o + " + "
        objective += "0;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
    os.system("lp_solve "+filename +"> "+sol_file)
def APS(K,N):
    top = K**math.ceil(math.log(N,K))
    bottom = K**math.floor(math.log(N,K))
    if (top==N):
        return top
    else:
        aps = K**math.floor(math.log(N,K))
        aps = aps*math.floor(math.log(N,K))
        while ((K*bottom)+K-1<=N):
            bottom+=K-1
            aps+=1
            aps+=(K-1)*math.ceil(math.log(N,K))
        aps+=(N-bottom)*math.ceil(math.log(N,K))
        aps+=1
        return aps
def calc_cost(n):
    Sumi = 0
    Sumo = 0
    for i in n.inputs:
        Sumi+=(1/len(i.fanouts))
    for o in n.fanouts:
        Sumo+=(1/len(n.fanouts))
    return Sumi-Sumo
def Permutations(sinks):
    perm = []
    if (sinks <=14): #was 15
        for p in range(1,(2**sinks)):
            plocal = []
            order = str(bin(p)[2:])
            while (len(order)<sinks):#add leading 0s
                order =  "0"+order
            i=sinks-1
            for et in order:
                if (et=='1'):
                    plocal.append(i)
                i=i-1
            perm.append(plocal.copy())
    else:
        for p in range(1,(2**14)):
            order = random.randint(1,2**sinks)
            plocal = []
            order = str(bin(order)[2:])
            while (len(order)<sinks):#add leading 0s
                order =  "0"+order
            i=sinks-1
            for et in order:
                if (et=='1'):
                    plocal.append(i)
                i=i-1
            perm.append(plocal.copy())
        
    return perm
                
def Formulate_init_ILP(ntk,N,K):
    obj_function=[]
    with open('temp.txt','w') as temp:
        for n in ntk.netlist:
           # print(n.name)
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=0;\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"=D_outputs;\n")
            if(True):
                #Smin = APS(K,len(n.fanouts))
                    #Smin = Smin*(len(n.fanouts))
                #S_line = "APS_"+n.name+"=0"
                #APS_min = str(Smin)+"<=APS_"+n.name+";\n"
                spans = []
                obj_function.append(str(calc_cost(n))+" D_"+n.name)
                for f in n.fanouts:
                    #weight = 1/len(n.fanouts)
                    #objfun="C_"+n.name+"_"+f.name
                    #obj_function.append(str(weight)+" "+objfun)
                    line = "1<="+"D_"+f.name+" - D_"+n.name+";\n"
                    temp.write(line)
                    #line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ " <= "+ str(N)+";\n"
                    #temp.write(line)
                        #line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ str(N) + " "+sfun+" <= "+ str(N)+";\n"
                    if (len(n.fanouts)>1):
                        #line = minfanout+"<="+objfun+";\n"
                        #temp.write(line)
                        line = "Span_"+n.name+"_"+f.name+" -"+"D_"+f.name+" + D_"+n.name+"=1;\n"
                        temp.write(line)
                        #line = "1<=S_"+n.name+"_"+f.name+"<="+str(+";\n"
                        #temp.write(line)
                        line = "1<=Span_"+n.name+"_"+f.name+";\n"
                        temp.write(line)
                        S_line= "Span_"+n.name+"_"+f.name
                        spans.append(S_line)
                if (len(n.fanouts)>1):
                    perm = Permutations(len(n.fanouts))
                    for subtree in perm:
                        Smin = APS(K,len(subtree))
                        APS_min = str(Smin)+"<=0"
                        for node in subtree:
                            APS_min+=" + "+spans[node]
                        APS_min+=";\n"
                        temp.write(APS_min)
                    #S_line+=";\n"
                    #temp.write(S_line) 
                    #temp.write(APS_min)
    filename = ntk.name+"_"+str(N)+".lp"
    sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    #print("made temp and lp")
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Min: "
        for o in obj_function:
            objective += o + " + "
        objective += "0;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
    #print("Solving Initital Levels")
    os.system("lp_solve "+filename +"> "+sol_file)           
def Formulate_init(ntk,N,K):
    obj_function=[]
    with open('temp.txt','w') as temp:
        for n in ntk.netlist:
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=0;\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"=D_outputs;\n")
            else:
                #Smin = APS(K,len(n.fanouts))
                    #Smin = Smin*(len(n.fanouts))
                #S_line = "APS_"+n.name+"=0"
                #APS_min = str(Smin)+"<=APS_"+n.name+";\n"
                spans = []
                for f in n.fanouts:
                    weight = 1/len(n.fanouts)
                    objfun="C_"+n.name+"_"+f.name
                    obj_function.append(str(weight)+" "+objfun)
                    line = "1<="+"D_"+f.name+" - D_"+n.name+";\n"
                    temp.write(line)
                    line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ " <= "+ str(N)+";\n"
                    temp.write(line)
                        #line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ str(N) + " "+sfun+" <= "+ str(N)+";\n"
                    if (len(n.fanouts)>1):
                        #line = minfanout+"<="+objfun+";\n"
                        #temp.write(line)
                        line = "Span_"+n.name+"_"+f.name+" +1="+"D_"+f.name+" - D_"+n.name+";\n"
                        temp.write(line)
                        #line = "1<=S_"+n.name+"_"+f.name+"<="+str(+";\n"
                        #temp.write(line)
                        line = "1<=Span_"+n.name+"_"+f.name+";\n"
                        temp.write(line)
                        S_line= "Span_"+n.name+"_"+f.name
                        spans.append(S_line)
                if (len(n.fanouts)>1):
                    perm = Permutations(len(n.fanouts))
                    for subtree in perm:
                        Smin = APS(K,len(subtree))
                        APS_min = str(Smin)+"<=0"
                        for node in subtree:
                            APS_min+=" + "+spans[node]
                        APS_min+=";\n"
                        temp.write(APS_min)
                    #S_line+=";\n"
                    #temp.write(S_line) 
                    #temp.write(APS_min)
    filename = ntk.name+"_"+str(N)+".lp"
    sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Min: "
        for o in obj_function:
            objective += o + " + "
        objective += "0;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
    print("Solving Initial Levels")
    os.system("lp_solve "+filename +"> "+sol_file)
    
def Formulate_init_CPLEX(ntk,N,K):
    
    obj_function=[]
    constraints = 0
    with open('temp.txt','w') as temp:
        temp.write("Subject To\nXNULL=0\n")
        for n in ntk.netlist:
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=1\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"-D_outputs=0\n")
            else:
                #Smin = APS(K,len(n.fanouts))
                    #Smin = Smin*(len(n.fanouts))
                #S_line = "APS_"+n.name+"=0"
                #APS_min = str(Smin)+"<=APS_"+n.name+";\n"
                spans = []
                for f in n.fanouts:
                    weight = 1/len(n.fanouts)
                    objfun="C_"+n.name+"_"+f.name
                    obj_function.append(str(weight)+" "+objfun)
                    line = objfun + ">=0\n"
                    temp.write(line)
                    line = "D_"+f.name+" - D_"+n.name+">=1\n"
                    temp.write(line)
                    line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ " <= "+ str(N)+"\n"
                    temp.write(line)
                        #line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ str(N) + " "+sfun+" <= "+ str(N)+";\n"
                    if (len(n.fanouts)>1):
                        #line = minfanout+"<="+objfun+";\n"
                        #temp.write(line)
                        line = "Span_"+n.name+"_"+f.name+"-D_"+f.name+" + D_"+n.name+" = -1\n"
                        temp.write(line)

                        #line = "1<=S_"+n.name+"_"+f.name+"<="+str(+";\n"
                        #temp.write(line)
                        line = "Span_"+n.name+"_"+f.name+">=1\n"
                        temp.write(line)
                        S_line= "Span_"+n.name+"_"+f.name
                        spans.append(S_line)
                if (len(n.fanouts)>1):
                    perm = Permutations(len(n.fanouts))
                    for subtree in perm:
                        Smin = APS(K,len(subtree))
                        APS_min = ""#str(Smin)
                        for node in subtree:
                            APS_min+=spans[node]+" + "
                        APS_min+="XNULL>= "+str(Smin)+"\n"
                        temp.write(APS_min)
                    #S_line+=";\n"
                    #temp.write(S_line) 
                    #temp.write(APS_min)
    filename = "problem.lp" #ntk.name+"_"+str(N)+".lp"
    #sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Minimize\n "
        for o in obj_function:
            objective += o + " + "
        objective += "XNULL;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
            constraints+=1
        lp.write("end")
    print("Solving Initial Levels with "+ str(constraints)+ " constraints")
    ti = time.time()
    os.system("./solve > junk.txt")#"lp_solve "+filename +"> "+sol_file)
    return (time.time()-ti)











def Formulate_init_copy(ntk,N,K):
    obj_function=[]
    with open('temp.txt','w') as temp:
        for n in ntk.netlist:
            if (n.gate_type =="PI"):
                temp.write("D_"+n.name+"=1;\n")
            if (n.gate_type=="PO"):
                temp.write("D_"+n.name+"=D_outputs;\n")
            else:
                Smin = APS(K,len(n.fanouts))
                    #Smin = Smin*(len(n.fanouts))
                S_line = "APS_"+n.name+"=0"
                APS_min = str(Smin)+"<=APS_"+n.name+";/n"
                if (len(n.fanouts)>1):
                    minfanout = "C_"+n.name
                    obj_function.append("-1 "+minfanout)
                for f in n.fanouts:
                    objfun="C_"+n.name+"_"+f.name
                    minfanout = "C_"+n.name
                    sfun = "0"
                    if (len(n.fanouts)>1):
                        sfun = "S_"+n.name+"_"+f.name
                    obj_function.append(objfun)
                    line = "1<="+"D_"+f.name+" - D_"+n.name+";\n"
                    temp.write(line)
                    line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ " <= "+ str(N)+";\n"
                    temp.write(line)
                        #line = "D_"+f.name+" - D_"+n.name+ "- "+str(N)+" "+objfun+ " "+ str(N) + " "+sfun+" <= "+ str(N)+";\n"
                    if (len(n.fanouts)>1):
                        line = minfanout+"<="+objfun+";\n"
                        temp.write(line)
                        line = "Span_"+n.name+"_"+f.name+" +1="+"D_"+f.name+" - D_"+n.name+";\n"
                        temp.write(line)
                        #line = "1<=S_"+n.name+"_"+f.name+"<="+str(+";\n"
                        #temp.write(line)
                        line = "1<=Span_"+n.name+"_"+f.name+";\n"
                        temp.write(line)
                        S_line+= " + Span_"+n.name+"_"+f.name
                if (len(n.fanouts)>1):
                    S_line+=";\n"
                    temp.write(S_line) 
                    temp.write(APS_min)
    filename = ntk.name+"_"+str(N)+".lp"
    sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    lines = []
    with open('temp.txt','r') as temp:
        lines = temp.readlines()
    with open(filename,'w') as lp:
        objective = "Min: "
        for o in obj_function:
            objective += o + " + "
        objective += "0;\n"
        lp.write(objective)
        for line in lines:
            lp.write(line)
    os.system("lp_solve "+filename +"> "+sol_file)

def Read_Solution_CPLEX(ntk,N):
    #print(ntk.s_dict)
    sol_file = "problem_sol.txt"#ntk.name+"_"+str(N)+"_sol.txt"
    cost = 0
    buff_cost = 0
    buff_cost2=0
    buff_cost3=0
    buff_cost4 = 0
    with open(sol_file,'r') as sol:
        for line in sol:
            if (line.split()[1][0]=="C"): #calculate cost
                result = line.split()
                cost += math.ceil(float(result[2]))
                buff_cost += math.ceil((math.ceil(float(result[2]))-1)/2)
                buff_cost2 += math.ceil((math.ceil(float(result[2]))-1)/3)
                buff_cost3 += math.ceil((math.ceil(float(result[2]))-1)/4)
                buff_cost4 += math.ceil((math.ceil(float(result[2]))-1)/5)
            if (line.split()[1][0]=="D"): #store depth values
                result = line.split()
                if (result[1].split("_")[1]=="outputs"):
                    continue
                else:
                    if "splitter" in result[1].split("_")[1]: #assign depth value to splitter
                        value = math.ceil(float(result[2]))
                        ntk.splitters[ntk.s_dict[result[1].split("_")[1]]].depth=value
                    else:
                        value = math.ceil(float(result[2]))
                        ntk.Obj(result[1].split("_")[1]).depth =value
                        ntk.Obj(result[1].split("_")[1]).depth_id =value
                        #print(result[0].split("_")[1]+" :" +str(value)) #assign depth value to gate
    cost += len(ntk.splitters)
    buff_cost+=len(ntk.splitters)
    buff_cost2+=len(ntk.splitters)
    buff_cost3+=len(ntk.splitters)
    return cost, [buff_cost,buff_cost2,buff_cost3,buff_cost4]









    
def Read_Solution(ntk,N):
    #print(ntk.s_dict)
    sol_file = ntk.name+"_"+str(N)+"_sol.txt"
    cost = 0
    buff_cost = 0
    buff_cost2=0
    buff_cost3=0
    with open(sol_file,'r') as sol:
        for line in sol:
            if (line[0]=="C"): #calculate cost
                result = line.split()
                cost += math.ceil(float(result[1]))
                buff_cost += math.ceil((math.ceil(float(result[1]))-1)/2)
                buff_cost2 += math.ceil((math.ceil(float(result[1]))-1)/3)
                buff_cost3 += math.ceil((math.ceil(float(result[1]))-1)/4)
            if (line[0]=="D"): #store depth values
                result = line.split()
                if (result[0].split("_")[1]=="outputs"):
                    continue
                else:
                    if "splitter" in result[0].split("_")[1]: #assign depth value to splitter
                        value = math.ceil(float(result[1]))
                        ntk.splitters[ntk.s_dict[result[0].split("_")[1]]].depth=value
                    else:
                        value = math.ceil(float(result[1]))
                        ntk.Obj(result[0].split("_")[1]).depth =value
                        ntk.Obj(result[0].split("_")[1]).depth_id =value
                        #print(result[0].split("_")[1]+" :" +str(value)) #assign depth value to gate
    cost += len(ntk.splitters)
    buff_cost+=len(ntk.splitters)
    buff_cost2+=len(ntk.splitters)
    buff_cost3+=len(ntk.splitters)
    return cost, [buff_cost,buff_cost2,buff_cost3]
def Gen_Netlist(filename,ntk,phases):
    with open(filename,'w') as file:
        header = "module "+ntk.name+"( "
        inputs = "input "
        outputs="output "
        for i in range(1,phases+1):
            header+="clk_"+str(i)+" , "
        for pi in ntk.PIs:
            header+=pi+" , "
            inputs +=pi+" , "
        for po in ntk.POs:
            header+=po +" , "
            outputs+=po +" , "
        header=header[:-2]+");\n\n"
        file.write(header)
        wire = "wire "
        for w in ntk.wires:
            wire += w + " , "
        for s in ntk.splitters:
            wire += s.name + " , "
        wire = wire[:-2]+";\n\n"
        inputs = inputs[:-2]+";\n"
        outputs = outputs[:-2]+";\n"
        file.write(inputs)
        file.write(outputs)
        file.write(wire)
        for n in ntk.netlist:
            file.write(str(n))
        for s in ntk.splitters:
            file.write(str(s))
        file.write("\nendmodule")
#def simulate(filename,golden,inputs,clks):#need to make libfile
#def make_TB(filename,golden,input_file,clks):
#def make_inputs(inputs):
#def compare_outputs(results,golden):
def less(cost,cost_min):
    if (cost[0]<cost_min[0]):
        return True
    elif(cost[0]>cost_min[0]):
        return False
    elif (cost[1]<cost_min[1]):
        return True
    elif (cost[1]>cost_min[1]):
        return False
    elif (cost[2]<cost_min[2]):
        return True
    else:
        return False
def Resolve_Fanouts(ntk,K,init,skip):
    Estimated_cost = 0
    rt=0
    if (init==0):
        for n in ntk.netlist:
            n.Find_Slack(skip)
            #if (n.slack>1):
            #    print(n.name)
        ntk.deleteSplitters()
    for n in ntk.netlist:
        if (len(n.fanouts)<=1):
            continue
        elif(len(n.fanouts)==2):
            s_name = "splitterfrom"+n.name
            split1 = Node(s_name,"splitter",[n],[0])
            ntk.add_splitter(split1)
            #print("Made New Splitter "+str(s_name))
            split1.connect_splitter(n.fanouts,n)
            Estimated_cost+=1
        #elif(len(n.fanouts)<=K and init==1):
         #   s_name = "splitterfrom"+n.name
          #  split1 = Node(s_name,"splitter",[n],[0])
           # ntk.add_splitter(split1)
            #split1.connect_splitter(n.fanouts,n)
            #print("Made New Splitter "+str(s_name))
        else:
            if (init==2):
                #ntk.deleteTree(n.splitter_out[0])
                ti = time.time()
                pt,delays,N = Build_Tree_init(n,K,skip)
                
                #pt,delays,N = Build_Tree(n,K,skip)
                #print("Entering Tree for:"+n.name+" with fanouts:")
                #print(delays)
                rt+= time.time()-ti
                Insert_Tree_init(ntk,pt,[0,N-1,0,0],n,n,delays)
                
                del pt,delays,N
                #print("Exiting with "+str(len(n.fanouts)) + " fanouts")
            else:
                ti =time.time()
                pt,dp,delays,N,cost = Build_Tree_init(n,K,skip)
                #print("Tree time for " + str(len(n.fanouts)) + " Fanouts is %s" % (time.time()-ti))
                rt += time.time()-ti
                #print("Entering Tree Init for:"+n.name+" with fanouts:")
                #print(delays)
                Insert_Tree_init(ntk,pt,[0,N-1,0,0],n,n,delays)
                
                Estimated_cost+=cost[2]
                #if (init==1):
                 #   for f in n.fanouts:
                  #      f.freeze_ASAP=1
                   # for n in ntk.netlist:
                    #    n.Find_ASAP()
                    #ntk.Fix_outputs()
                    #ntk.Set_ALAP()
                    #for n in ntk.netlist:
                     #   n.depth = n.ASAP
                del pt,dp,delays,N
    return rt
    #if (init==1):
     #   print("Estimated Cost after tree: "+str(Estimated_cost))
            
def Build_Tree_init(node,X,phase_skips):
    delays=[]
    N = 0
    recalc=0
    for f in node.fanouts:
        if (f.depth-node.depth-1<0):
            recalc = 1
        delays.append((f.depth-node.depth-1,f.name,f.slack))
        N+=1
    if (recalc==1):
        delays = []
        for f in node.fanouts:
            delays.append((f.depth_id-node.depth_id-1,f.name,f.slack))
    delays = []
    for f in node.fanouts:
        delays.append((1,f.name,0))
    #for f in node.fanouts:
    #    delays.append((f.ALAP-node.ALAP-1,f.name,0))
    #    latest=0
    #    N+=1
    delays.sort()  
    #print(delays)
    Max_d = delays[-1][0]+ 1 + math.ceil(math.log(N,X))
    #print(Max_d)
    if (math.ceil(math.log(N,X))<=0):
        Max_d = delays[-1][0]+ 1+1
    #Max_d = delays[-1][0]+delays[-1][2]+ 1 + math.ceil(math.log(N,X))
    inf = 700000
    dp = [[[[[5000,5000,5000]]*(Max_d+1)]*X]*N]*N
    pt = [[[[(-2,-2,-2)]*(Max_d+1)]*X]*N]*N
    p1 = [N,X]
    dp = numpy.array(dp)
    pt= numpy.array(pt)
    #init
    for s in range(1,min(p1)+1):
        for l in range(1,N-s+2):
            r = l+s-1
            wdelay = delays[l-1][0]
            if (s==1):
                for d in range(0,Max_d+1):
                    delta = abs(d-wdelay)
                    if (d>wdelay):
                        if (d>wdelay+delays[l-1][2]):
                            dp[l-1][l-1][s-1][d] = [delta,delta,0]
                        else:
                            dp[l-1][l-1][s-1][d] = [0,0,0]
                    else:
                        delta = math.floor(float(delta)/phase_skips)
                        dp[l-1][l-1][s-1][d] = [0,0,delta]
            else:
                for el in range(1,3):
                    dp[l-1][r-1][s-1][Max_d][el] = dp[l-1][r-2][s-2][Max_d][el] + dp[r-1][r-1][0][Max_d][el]
                dp[l-1][r-1][s-1][Max_d][0] = max(dp[l-1][r-2][s-2][Max_d][0],dp[r-1][r-1][0][Max_d][0])#,dp[l-1][r-1][s-1][Max_d][1])
    #find min
    for ln in range(1,N):#was 1 to N
        for l in range(1,N-ln+1):
            r = l+ln #check this
            #p2 = [X,ln+1]
            p2 = [X,ln+1]
            d = Max_d-1
            while (d>=0):
                for s in range(1,min(p2)+1):
                    if (s==1):
                        cost_min = [6000000,6000000,600000]
                        #cost_min=numpy.array(cost_min)
                        k_min = 0
                        d_min=0
                        for k in range(1,min(p2)+1):
                            for pr in range(1,phase_skips+1):
                                if (d+pr<=Max_d ):
                                    cost = dp[l-1][r-1][k-1][d+pr].copy()
                                    cost[2]= cost[2]+1
                                    if(less(cost,cost_min)):
                                        for el in range(1,3):
                                            cost_min[el] = cost[el]+0
                                        cost_min[0] = max(cost[0],0)
                                        k_min = k
                                        d_min = d+pr
                        pt[l-1][r-1][s-1][d] = (-1,k_min,d_min)
                        dp[l-1][r-1][s-1][d] = cost_min.copy()
                    else:
                        cost_min = [4000000,4000000,400000]
                        #cost_min=numpy.array(cost_min)
                        p_min = -1
                        k_min = -1
                        #d1_min = -1
                        #d2_min = -1
                        for k in range(1,s):
                            for p in range (l,r-s+k+1):###s+1??
                                cost1 = dp[l-1][p-1][k-1][d].copy()
                                cost2 = dp[p][r-1][s-k-1][d].copy()
                             #   cost1 = dp[l-1][p-1][s-2][d]
                              #  cost2 = dp[p][r-1][0][d]
                                for el in range(1,3):
                                    cost[el] = cost1[el]+cost2[el]
                                cost[0]=max(cost1[0],cost2[0])
                                if (less(cost,cost_min)):
                                    #for el in range(1,3):
                                     #   cost_min[el] = cost1[el]+cost2[el]
                                    cost_min = cost.copy()
                                    #print("Updated")
                                    k_min = k
                                    p_min = p
                        pt[l-1][r-1][s-1][d] = (p_min,k_min,-1)
                        dp[l-1][r-1][s-1][d] = cost_min.copy()

                                #cost1_min = 500000
                                #cost2_min = 500000
                                #d1_ = -1
                                #d2_ = -1
                                #for pr in range(1,phase_skips):
                                 #   cost1 = dp[l-1][p-1][k-1][d+pr]
                                  #  if (cost1<cost1_min):
                                   #     cost1_min = cost1
                                    #    d1_ = d+Pr
                                    #cost2 = dp[p][r-1][s-k-1][d+pr]
                                    #if (cost2<cost2_min):
                d=d-1
    return pt, dp,delays, N, dp[0][N-1][0][0]   
def Build_Tree(node,X,phase_skips):
    delays=[]
    N = 0
    for f in node.fanouts:
        delays.append((f.depth-node.depth-1,f.name,f.slack))
        N+=1
    delays.sort()  
    #print(delays)
    Max_d = delays[-1][0]+delays[-1][2]
    inf = 700000
    dp = [[[[5000]*(Max_d+1)]*X]*N]*N
    pt = [[[[(-2,-2,-2)]*(Max_d+1)]*X]*N]*N
    p1 = [N,X]
    dp = numpy.array(dp)
    pt= numpy.array(pt)
    #init
    for s in range(1,min(p1)+1):
        for l in range(1,N-s+2):
            r = l+s-1
            wdelay = delays[l-1][0]
            if (s==1):
                for d in range(0,Max_d+1):
                    delta = abs(d-wdelay)
                    if (d>wdelay):
                        if (d>wdelay+delays[l-1][2]):
                            dp[l-1][l-1][s-1][d] = inf
                        else:
                            dp[l-1][l-1][s-1][d] = 0
                    else:
                        delta = math.floor(float(delta)/phase_skips)
                        dp[l-1][l-1][s-1][d] = delta
            else:
                dp[l-1][r-1][s-1][Max_d] = dp[l-1][r-2][s-2][Max_d].copy() + dp[r-1][r-1][0][Max_d].copy()
    #find min
    for ln in range(1,N):
        for l in range(1,N-ln+1):
            r = l+ln #check this
            p2 = [X,ln+1]
            d = Max_d-1
            while (d>=0):
                for s in range(1,min(p2)+1):
                    if (s==1):
                        cost_min = 6000000
                        k_min = 0
                        d_min=0
                        for k in range(1,min(p2)+1):
                            for pr in range(1,phase_skips+1):
                                if (d+pr<=Max_d ):
                                    cost = dp[l-1][r-1][k-1][d+pr].copy() + 1
                                    if (cost<cost_min):
                                        cost_min = cost
                                        k_min = k
                                        d_min = d+pr
                        pt[l-1][r-1][s-1][d] = (-1,k_min,d_min)
                        dp[l-1][r-1][s-1][d] = cost_min
                    else:
                        cost_min = 4000000
                        p_min = -1
                        k_min = -1
                        #d1_min = -1
                        for k in range(1,s):
                            for p in range (l,r-s+k+1):
                                cost1 = dp[l-1][p-1][k-1][d].copy()
                                cost2 = dp[p][r-1][s-k-1][d].copy()
                                cost = cost1+cost2
                                if (cost<cost_min):
                                    cost_min = cost
                                    k_min = k
                                    p_min = p
                        pt[l-1][r-1][s-1][d] = (p_min,k_min,-1)
                        dp[l-1][r-1][s-1][d] = cost_min
                                #cost1_min = 500000
                                #cost2_min = 500000
                                #d1_ = -1
                                #d2_ = -1
                                #for pr in range(1,phase_skips):
                                 #   cost1 = dp[l-1][p-1][k-1][d+pr]
                                  #  if (cost1<cost1_min):
                                   #     cost1_min = cost1
                                    #    d1_ = d+Pr
                                    #cost2 = dp[p][r-1][s-k-1][d+pr]
                                    #if (cost2<cost2_min):
                d=d-1
    #print(dp[0][N-1][0][0])
    #print(dp)
    return pt, delays, N

def Insert_Tree(ntk,pt,state,root,source, delays):
    step = pt[state[0]][state[1]][state[2]][state[3]]
    #if (step[1]==-2):
    #    print(step)
    #print("In state:")
    #print(state)
    #print("Step:")
    #print(step)
    
    if (step[0]==-1):
        next_state = [state[0],state[1],step[1]-1,step[2]]
        #print("Jumping to State")
        #print(next_state)
        if(step[1]>1):
            name = "splitter"+ source.name + "to"+str(delays[state[0]][1])+str(delays[state[1]][1])
            #print(name)
            new_split = Node(name,"splitter",[root],[0])
            #print("Made New Splitter: "+new_split.name)
            #print(len(root.fanouts))
            ntk.add_splitter(new_split)
            #print("Added to Network!!")
            #print(len(root.fanouts))
            if (state[1]-state[0] == step[1]-1):#Fanout to each node
                #print("Found Multiple Sinks")
                for s in range(state[0],state[1]+1):
                    sink = ntk.Obj(delays[s][1])
                    new_split.connect_splitter([sink],source)
                    if (state[3]>delays[s][0]):
                        sink.depth = sink.depth+state[3]-delays[s][0]
                        sink.slack = sink.slack -(state[3]-delays[s][0])
                        #print("With Slack:" +str(delays[s][2])+" Retimed "+delays[s][1]+" from "+str(delays[s][0])+" to "+str(state[3]))
                    #print(len(root.fanouts))
            else:
                Insert_Tree(ntk,pt,next_state,new_split,source,delays)
        else:
            Insert_Tree(ntk,pt,next_state,root,source,delays)
    else:
        next_state = [state[0],step[0]-1,step[1]-1,state[3]]
        next_state2 = [step[0],state[1],state[2]-step[1],state[3]]
        if (state[1]-state[0] == state[2]):#Fanout to each node
            for s in range(state[0],state[1]+1):
                sink = ntk.Obj(delays[s][1])
                root.connect_splitter([sink],source)
                if (state[3]>delays[s][0]):
                    sink.depth = sink.depth+state[3]-delays[s][0]
                    sink.slack = sink.slack -(state[3]-delays[s][0])
                    #print("With Slack:" +str(delays[s][2])+" Retimed " +delays[s][1]+" from "+str(delays[s][0])+" to "+str(state[3]))
        else:
            if (state[0]!=step[0]-1):
                Insert_Tree(ntk,pt,next_state,root,source,delays)
            else:
                sink = ntk.Obj(delays[state[0]][1])#left fanout is to 1 node
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[0]][0]):
                    sink.depth = sink.depth+state[3]-delays[state[0]][0]
                    sink.slack = sink.slack -(state[3]-delays[state[0]][0])
                    #print("With Slack:" +str(delays[state[0]][2])+" Retimed "+delays[state[0]][1]+" from "+str(delays[state[0]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
            if (state[1]!=step[0]):
                Insert_Tree(ntk,pt,next_state2,root,source,delays)
            else: #right fanout is to 1 node
                sink = ntk.Obj(delays[state[1]][1])
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[1]][0]):
                    sink.depth = sink.depth+state[3]-delays[state[1]][0]
                    sink.slack = sink.slack -(state[3]-delays[state[1]][0])
                    #print("With Slack:" +str(delays[state[1]][2])+" Retimed "+delays[state[1]][1]+" from "+str(delays[state[1]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
        #   print("Reached Sink:"+str(state[1]))
def Insert_Tree_init(ntk,pt,state,root,source, delays):
    step = pt[state[0]][state[1]][state[2]][state[3]]
    if (step[0]==-2):
        print(step)
        print("In state:")
        print(state)
        print("Step:")
        print(step)
    
    if (step[0]==-1):
        next_state = [state[0],state[1],step[1]-1,step[2]]
        if(step[1]>1):
            name = "splitter"+ source.name + "to"+str(delays[state[0]][1])+str(delays[state[1]][1])
            #print(name)
            new_split = Node(name,"splitter",[root],[0])
            #print("Made New Splitter: "+new_split.name)
            #print(len(root.fanouts))
            ntk.add_splitter(new_split)
            #print("Added to Network!!")
            #print(len(root.fanouts))
            if (state[1]-state[0] == step[1]-1):#Fanout to each node
                for s in range(state[0],state[1]+1):
                    sink = ntk.Obj(delays[s][1])
                    new_split.connect_splitter([sink],source)
                    if (state[3]>delays[s][0]):
                        sink.depth = sink.depth+state[3]-delays[s][0]
                        sink.slack = sink.slack -(state[3]-delays[s][0])
                        #print("With Slack:" +str(delays[s][2])+" Retimed "+delays[s][1]+" from "+str(sink.depth-state[3]+delays[s][0])+" to "+str(sink.depth))
                    #print(len(root.fanouts))
            else:
                Insert_Tree_init(ntk,pt,next_state,new_split,source,delays)
        else:
            Insert_Tree_init(ntk,pt,next_state,root,source,delays)
    else:
        next_state = [state[0],step[0]-1,step[1]-1,state[3]]
        next_state2 = [step[0],state[1],state[2]-step[1],state[3]]
        if (state[1]-state[0] == state[2]):#Fanout to each node
            for s in range(state[0],state[1]+1):
                sink = ntk.Obj(delays[s][1])
                root.connect_splitter([sink],source)
                if(state[3]>delays[s][0]):
                    sink.depth = sink.depth+state[3]-delays[s][0]
                    sink.slack = sink.slack -(state[3]-delays[s][0])
                    #print("With Slack:" +str(delays[s][2])+" Retimed " +delays[s][1]+" from "+str(delays[s][0])+" to "+str(state[3]))
        else:
            if (state[0]!=step[0]-1):
                Insert_Tree_init(ntk,pt,next_state,root,source,delays)
            else:
                sink = ntk.Obj(delays[state[0]][1])#left fanout is to 1 node
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[0]][0]):
                    sink.depth = sink.depth+state[3]-delays[state[0]][0]
                    sink.slack = sink.slack -(state[3]-delays[state[0]][0])
                    #print("With Slack:" +str(delays[state[0]][2])+" Retimed "+delays[state[0]][1]+" from "+str(delays[state[0]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
            if (state[1]!=step[0]):
                Insert_Tree_init(ntk,pt,next_state2,root,source,delays)
            else: #right fanout is to 1 node
                sink = ntk.Obj(delays[state[1]][1])
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[1]][0]):
                    sink.depth = sink.depth+state[3]-delays[state[1]][0]
                    sink.slack = sink.slack -(state[3]-delays[state[1]][0])
                    #print("With Slack:" +str(delays[state[1]][2])+" Retimed "+delays[state[1]][1]+" from "+str(delays[state[1]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
        #   print("Reached Sink:"+str(state[1]))
def Insert_Tree_init_ASAP(ntk,pt,state,root,source, delays):
    step = pt[state[0]][state[1]][state[2]][state[3]]
    #if (step[1]==-2):
    #    print(step)
    #print("In state:")
    #print(state)
    #print("Step:")
    #print(step)
    
    if (step[0]==-1):
        next_state = [state[0],state[1],step[1]-1,step[2]]
        #print("Jumping to State")
        #print(next_state)
        if(step[1]>1):
            name = "splitter"+ source.name + "to"+str(delays[state[0]][1])+str(delays[state[1]][1])
            #print(name)
            new_split = Node(name,"splitter",[root],[0])
            #print("Made New Splitter: "+new_split.name)
            #print(len(root.fanouts))
            ntk.add_splitter(new_split)
            #print("Added to Network!!")
            #print(len(root.fanouts))
            if (state[1]-state[0] == step[1]-1):#Fanout to each node
                #print("Found Multiple Sinks")
                for s in range(state[0],state[1]+1):
                    sink = ntk.Obj(delays[s][1])
                    new_split.connect_splitter([sink],source)
                    if (state[3]>delays[s][0]):
                        sink.ASAP = sink.ASAP+state[3]-delays[s][0]
                        if (sink.ASAP>sink.ALAP):
                            sink.ALAP= sink.ASAP
                        #sink.slack = sink.slack -(state[3]-delays[s][0])
                        #print("With Slack:" +str(delays[s][2])+" Retimed "+delays[s][1]+" from "+str(delays[s][0])+" to "+str(state[3]))
                    #print(len(root.fanouts))
            else:
                Insert_Tree_init_ASAP(ntk,pt,next_state,new_split,source,delays)
        else:
            Insert_Tree_init_ASAP(ntk,pt,next_state,root,source,delays)
    else:
        next_state = [state[0],step[0]-1,step[1]-1,state[3]]
        next_state2 = [step[0],state[1],state[2]-step[1],state[3]]
        if (state[1]-state[0] == state[2]):#Fanout to each node
            for s in range(state[0],state[1]+1):
                sink = ntk.Obj(delays[s][1])
                root.connect_splitter([sink],source)
                if (state[3]>delays[s][0]):
                    sink.ASAP = sink.ASAP+state[3]-delays[s][0]
                    if (sink.ASAP>sink.ALAP):
                        sink.ALAP= sink.ASAP
                    #sink.slack = sink.slack -(state[3]-delays[s][0])
                    #print("With Slack:" +str(delays[s][2])+" Retimed " +delays[s][1]+" from "+str(delays[s][0])+" to "+str(state[3]))
        else:
            if (state[0]!=step[0]-1):
                Insert_Tree_init_ASAP(ntk,pt,next_state,root,source,delays)
            else:
                sink = ntk.Obj(delays[state[0]][1])#left fanout is to 1 node
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[0]][0]):
                    sink.ASAP = sink.ASAP+state[3]-delays[state[0]][0]
                    if (sink.ASAP>sink.ALAP):
                        sink.ALAP= sink.ASAP
                    #sink.slack = sink.slack -(state[3]-delays[state[0]][0])
                    #print("With Slack:" +str(delays[state[0]][2])+" Retimed "+delays[state[0]][1]+" from "+str(delays[state[0]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
            if (state[1]!=step[0]):
                Insert_Tree_init_ASAP(ntk,pt,next_state2,root,source,delays)
            else: #right fanout is to 1 node
                sink = ntk.Obj(delays[state[1]][1])
                #print("Connecting "+root.name + " to "+ sink.name)
                root.connect_splitter([sink],source)
                if (state[3]>delays[state[1]][0]):
                    sink.ASAP=sink.ASAP+state[3]-delays[state[1]][0]
                    if (sink.ASAP>sink.ALAP):
                        sink.ALAP= sink.ASAP
                    #sink.slack = sink.slack -(state[3]-delays[state[1]][0])
                    #print("With Slack:" +str(delays[state[1]][2])+" Retimed "+delays[state[1]][1]+" from "+str(delays[state[1]][0])+" to "+str(state[3]))
                #print(len(root.fanouts))
        #   print("Reached Sink:"+str(state[1]))            
                                      
                        
                            
                    

def Insert_Buffers(ntk,N):
    sol_file = "problem_sol.txt"#ntk.name+"_"+str(N)+"_sol.txt"
    with open(sol_file,'r') as sol:
        for line in sol:
            if (line.split()[1][0]=="C"): #calculate cost
                result = line.split()
                cost = math.ceil(float(result[2]))
                #insert cost buffers between the i and j nodes
                i = result[1].split('_')[1]
                j = result[1].split('_')[2]
                i_name = i
                i_first = i_name
                j_name = j
                j_first = j_name
                is_split = 0
                while(cost>0):
                    if "splitter" in i_name and "buf" not in i_name:
                        i = ntk.splitters[ntk.s_dict[i_name]]
                    else: 
                        i = ntk.Obj(i_name)
                    if "splitter" in j_name:
                        j=ntk.splitters[ntk.s_dict[j_name]]
                    else:
                        j=ntk.Obj(j_name)
                    bufName = "buf_"+i_first+"_"+j_first+"_"+str(cost)
                    buf = Node(bufName,"buf",[i],[0])
                    ntk.add(buf)
                    j.insertbuf(i,buf)
                    buf.depth = i.depth+N
                    i = buf
                    j_name = j.name
                    i_name = i.name
                    cost += -1

import time
def Algorithm(name,fanout,phase_skips,phases):
    circ = Ntk(name)
    start_time= time.time()
    phase_time = 0.0
    tree_time = 0.0
    circ.parse("Notebook_Files/"+name+".v")
    gate_count=0
    for n in circ.netlist:
        if (n.gate_type!="PO" and n.gate_type!="PI"):
            gate_count+=1
    print("Parsed Circuit " +name+" has gate count "+str(gate_count))
    #circ = circuit
    #print("avlie")
    phase_time +=Formulate_init_CPLEX(circ,phase_skips,fanout)
    #print("Total Time: %s seconds " % (phase_time))
    #Formulate_CPLEX(circ,phase_skips)

    best_cost,buff_cost =Read_Solution_CPLEX(circ,phase_skips)

    #for n in circ.netlist:
    #    n.Find_Slack(phase_skips)
    #print("Estimated Cost: "+str(best_cost))
    ######I dont think these were used?? circ.Fix_outputs()
    ######circ.Set_ALAP()
    circ.phases = phases
    #print("Init Trees")
    tree_time+=Resolve_Fanouts(circ,fanout,1,phase_skips)
    #print("Tree time: %s seconds " % (tree_time))
    #return pt,dp
    #print(len(circ.splitters))
    phase_time+=Formulate_CPLEX(circ,phase_skips)
    for n in circ.netlist:
        n.Find_Slack(phase_skips)
    #print("Reading Solution")
    best_cost,buff_cost =Read_Solution_CPLEX(circ,phase_skips)
    cost = 0
    iteration = 1
    saved=[]
    #print("Chain Retiming Cost ="+str(buff_cost))
    print("Initial Cost: "+str(best_cost))
    if (phase_skips==1):
        saved = buff_cost
    while (cost<best_cost):
        for n in circ.netlist:
            n.Find_Slack(phase_skips)
        tree_time+=Resolve_Fanouts(circ,fanout,0,phase_skips)
        #print(len(circ.splitters))
        phase_time+=Formulate_CPLEX(circ,phase_skips)
        cost,buff_cost = Read_Solution_CPLEX(circ,phase_skips)
        iteration+=1
        if (cost<best_cost):
            best_cost = cost
            cost = 0
            print("Iteration "+str(iteration)+": "+str(best_cost))
        else:
            print("No Improvement Found in Iteration "+str(iteration) + " at cost "+str(cost))
            circ.CleanNtk()
            #print("Inserting Buffers")
            saved = buff_cost
            Insert_Buffers(circ,phase_skips)
        
    #print("Best Cost Found is: "+str(best_cost))
    circ.set_phases()
    netlist_name = name+"_"+str(phases)+"phases_"+str(phase_skips-1)+"_netlist.v"
    Gen_Netlist(netlist_name,circ,phases)
    #print("Generated Netlist: "+netlist_name)
    test =circ.verify(phase_skips)
    print("Total Time: %s seconds " % (time.time()-start_time))
    print("Time in phase assignment %s " % (phase_time))
    print("Time in tree construction %s " % (tree_time))
    if (not test):
        cost = 10000000
    return circ,best_cost,saved[0],saved[1],saved[2],saved[3]
def Run_Benchmarks():
    Phase4=[]
    NPhase=[]
    circuit = "c432"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    exit()
    circuit = "c499"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c880"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c1355"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c1908"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c2670"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c3540"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c5315"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c6288"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "c7552"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "mult8"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "counter16"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "counter32"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "counter64"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "counter128"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    circuit = "alu32"
    circ4,cost4,s1,s2,s3,s4 = Algorithm(circuit,4,2,8)
    Phase4.append((cost4,circuit,s1,s2,s3,s4))
    #circuit = "alu32"
    #circuit = "c7552"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,2,8)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c2670"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,3,12)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c6288"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,4,16)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c499"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c880"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c1355"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c1908"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c2670"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c3540"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c5315"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))
    #circuit = "c6288"
    #circ4,cost4,s1,s2,s3 = Algorithm(circuit,4,1,4)
    #Phase4.append((cost4,circuit,s1,s2,s3))"""
    return Phase4, NPhase
def print_results(p4,np):
    print("2Skip Results\n_____________")
    total1 = 0
    total2 = 0
    for c in p4:
        print(c[1]+"  |  "+str(c[0]) + " | "+str(c[2]))
        total1 += c[0]
        total2+=c[2]
    print("Sum | "+str(total1) + " | " + str(total2))    
    print("\n\n3-Skip Results\n_____________")
    total3=0
    for c in np:
        print(c[1]+"  |  "+str(c[0]))
        total3+= c[0]
    print("Sum | "+ str(total3))
def print_results2(p4):
    total0=0
    total1=0
    total2=0
    total3=0
    total4=0
    for c in p4:
        print(c[1]+" | "+str(c[0]) + " | " + str(c[2]) + " | " +str(c[3]) + " | " + str(c[4]) + " | " + str(c[5]))
        total0+= c[0]
        total1+= c[2]
        total2+= c[3]
        total3+= c[4]
        total4+= c[4]
    print("Sum | "+str(total0) + " | " + str(total1) + " | " + str(total2) + " | " + str(total3)+ " | " + str(total4))    
def string_to_file(string,path):
    with open(path,'w') as f:
        f.write(string)
def file_to_string(path):
    with open(path,'r') as f:
        return f.read()
  
p4,np = Run_Benchmarks()
print_results2(p4)
#path = "Notebook_Files/counter16.v"
#string_to_file(file_to_string(path).replace("_",""),path)
#path = "Notebook_Files/counter32.v"
#string_to_file(file_to_string(path).replace("_",""),path)
#path = "Notebook_Files/counter64.v"
#string_to_file(file_to_string(path).replace("_",""),path)
#path = "Notebook_Files/counter128.v"
#string_to_file(file_to_string(path).replace("_",""),path)
#Algorithm("c7552",4,1,4)
#Algorithm("c7552",4,2,8)
