# -*- coding: utf-8 -*-
"""
Created on Wed Apr 18 17:24:37 2018

@author: Ed Danileyko
"""

# Initiate count of dupes, breaks, and invalid messages.
dupeCount = dupeQty = breakCount = breakQty = invalidCount = 0

# parentOrders (client-side): key is tag37=OrderID
# childOrders (exchange-side): key is tag11=ClientOrderID
# orderMap contains child order to parent order mapping.
parentOrders = childOrders = orderMap = {}

beginReport = True


class ParentOrder(object):
    """Object representing a parent order.
        - orderID: Tag37=OrderID.
        - clientOrderID: Tag11=ClientOrderID.
        - inboundQtyDone: Increment from ChildOrder execution qtys.
        - fills: Set of execution ids.
        - childOrders: Set of ChildOrder objects.
        """
    def __init__(self, orderID):
        self.orderID = orderID
        self.clientOrderID = ""
        self.inboundQtyDone = 0
        self.outboundQtyDone = 0
        self.fills = set()
        self.childOrders = set()


class ChildOrder(object):
    """Object representing a child order.
        - parentID: Value should be present in map file.
        - fills: Set of all tag17=ExecID.
        """
    def __init__(self):
        self.parentID = None
        self.fills = set()

        
def parse(fixlog):
    """Reads a FIX log and constructs a dictionary of subdictionaries
    in which key=FIX tag and value=FIX value. Invalid messages are counted
    towards the global invalid message count if there is no tag or value
    present. Messages are validated both by validateFIX() as well as exception
    handling in the event that a value is missing. Not sure if this is
    according to protocol though...
    """
    messages = []
    global invalidCount
    with open(fixlog, 'r') as fixlog:
        for line in fixlog:
            try:
                message = {field.split('=')[0]: field.split('=')[1] for field in line[:-2].split('')}
                if validateFIX(message):
                    messages.append(message)
                else:
                    reportBreak("INVALID_MESSAGE", "", 0, "", "", "")
                    invalidCount += 1
            except IndexError:
                # Error is raised if tag or value is missing
                reportBreak("INVALID_MESSAGE", "", 0, "", "", "")
                invalidCount += 1
                pass
    return messages
    
    
def validateFIX(message):
    """Performs minimum message validation.
    (Code for more exhaustive validation based on conditional tags could go here).
    """
    if "35" not in message.keys():
        return False
    messageType = message["35"]
    if messageType == "D":
        # only CliOrdId need be present to validate 35=D
        if "11" not in message.keys() or len(message["11"]) == 0:
            return False
    # 35=8 messages need to have 150, 37, and 11
    if messageType == "8":
        if "150" not in message.keys() or len(message["150"]) == 0:
            return False
        if "37" not in message.keys() or len(message["37"]) == 0:
            return False
        if "11" not in message.keys() or len(message["11"]) == 0:
            return False
        execType = message["150"]
        # for fills, checks that qty and px are present
        if execType in ["1", "2"]:
            if "31" not in message.keys() or len(message["31"]) == 0:
                return False
            if "32" not in message.keys() or len(message["32"]) == 0:
                return False
    return True


def mapChildtoParent(mapFile):
    """Populates an order map dict with childID=parentID.
    """
    with open(mapFile, 'r') as file:
        next(file)  # ignore header
        for line in file:
            try:
                childId, parentId = line.split(',')[0], line.split(',')[2][:-1]
            except IndexError:
                pass    # Maybe add error message to indicate corrupt map file.
            if childId not in orderMap.keys():
                orderMap[childId] = parentId


def getParentOrder(childID):
    """Retrieves the ParentOrder associated with a childID.
    If successful, adds this object to parent orders dict.
    """
    parentOrder = None
    if childID in orderMap.keys():
        parentOrderID = orderMap[childID]
        if parentOrderID in parentOrders.keys():
            parentOrder = parentOrders[parentOrderID]
        else:
            parentOrder = ParentOrder(parentOrderID)
            parentOrders[parentOrderID] = parentOrder
    else:
        reportBreak("MAPPING_FAILURE", "", 0, 0, childID, "", "")
    return parentOrder

  
def processOutbound(log):
    """Processes exchange-side FIX log execution report 35=8 lines.
    - Creates new ChildOrder obj when a new tag11 is encountered and
    maps this to its ParentOrder obj.
    - Populates a parent order's child order set.
    - Populates a child orders execution set.
    - Increments child order's parent qty done.
    """
    for message in log:
        if message["35"] == "8":
            parent = None
            child = None
            childID = message["11"]
            if childID not in childOrders.keys():
                child = ChildOrder()
                childOrders[childID] = child
                parent = getParentOrder(childID)
                if parent is not None:
                    if childID not in parent.childOrders:
                        child.parentID = parent.orderID
                        parent.childOrders.add(childID)
            else:
                child = childOrders[childID]
                if child.parentID is not None:
                    parent = parentOrders[child.parentID]
            if message["150"] in ["1", "2"]:
                executionID = message["17"]
                if executionID not in child.fills:
                    qtyDone = int(message["32"])  # add to FIX validation a check if the value can be cast as int
                    child.fills.add(executionID)
                    if parent is not None:
                        parent.outboundQtyDone += qtyDone
                else:
                    reportBreak("DUPLICATE_FILL", executionID, qtyDone, childID, child.parentID, parentOrders[child.parentID].clientOrderID)   # What is 17=exe_5 ? this script checks for dupes based on 17=


def processInbound(log):
    """Processes client-side FIX log execution report lines.
    - Populates parentOrders dict with ParentOrder objs.
    - Adds entry to ParentOrder.fills
    - Updates ParentOrder.inboundQtyDone
    """
    for message in log:
        if message["35"] == "8":
            orderID = message["37"]
            parent = None
            if orderID not in parentOrders.keys():
                parent = ParentOrder(orderID)
                parent.clientOrderID = message["11"]
                parentOrders[orderID] = parent
            else:
                parent = parentOrders[orderID]
                parent.clientOrderID = message["11"]
            if message["150"] in ["1", "2"]:
                executionID = message["17"]
                if executionID not in parent.fills:
                    qtyDone = int(message["32"])
                    parent.fills.add(executionID)
                    parent.inboundQtyDone += qtyDone
          
          
def writeCsv(outputcsv):
    """Writes output.csv which indicates status and health of all orders.
    """
    header = "clientid,parentid,is_healthy,num_child,inbound_exec_qty,outbound_exec_qty\n"
    with open(outputcsv, 'w+') as csv:
      csv.write(header)
      for order in parentOrders.values():
          clientid = order.clientOrderID
          parentid = order.orderID
          ishealthy = order.inboundQtyDone == order.outboundQtyDone
          childCount = len(order.childOrders)
          inboundExecQty = order.inboundQtyDone
          outboundExecQty = order.outboundQtyDone
          csv.write("{},{},{},{},{},{}\n".format(clientid, parentid, ishealthy, childCount, inboundExecQty, outboundExecQty))

          
def reportBreak(breakType, execId, qty, childOrderId, parentOrdId, cliOrdId):
    """Prints a message containing order break information to stdout.
    """
    global beginReport
    if beginReport:
        print("ERROR,TYPE,EXEC_ID,QTY,PX,CHILD_ORDER,PARENT_ORDER,CLIENT_ORDER")
        beginReport = False
    print("BREAK,{},{},{},{},{},{}".format(breakType, execId, qty, childOrderId, parentOrdId, cliOrdId))
    if breakType == "DUPLICATE":
        global dupeCount
        dupeCount = dupeCount + 1
        global dupeQty
        dupeQty = dupeQty + qty
    else:
        global breakCount
        breakCount = breakCount + 1
        global breakQty
        breakQty = breakQty + qty


if __name__ == '__main__':

    from os import path
    from sys import argv

    # Order mapping static file and recon output file.
    dir = path.dirname(__file__)
    idsfile, outputcsv = (path.join(dir, name) for name in ('ids.csv', 'output.csv'))

    inBoundLog  = path.join(dir, argv[1])
    outBoundLog = path.join(dir, argv[2])
    
    mapChildtoParent(idsfile)
    processOutbound(parse(outBoundLog))
    processInbound(parse(inBoundLog))

    writeCsv(outputcsv)
