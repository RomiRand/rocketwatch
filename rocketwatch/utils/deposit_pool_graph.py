from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np

from utils import solidity
from utils.rocketpool import rp

cached_image_commission = None
cached_image = None


def get_graph(current_commission):
    global cached_image_commission
    global cached_image
    if cached_image_commission == current_commission:
        cached_image.seek(0)
        return cached_image
    else:
        cached_image.close()

    current_node_demand = solidity.to_float(rp.call("rocketNetworkFees.getNodeDemand"))

    # get values from contracts
    min_fee = solidity.to_float(rp.call("rocketDAOProtocolSettingsNetwork.getMinimumNodeFee"), decimals=16)
    max_fee = solidity.to_float(rp.call("rocketDAOProtocolSettingsNetwork.getMaximumNodeFee"), decimals=16)
    if min_fee == max_fee:
        return None

    target_fee = solidity.to_float(rp.call("rocketDAOProtocolSettingsNetwork.getTargetNodeFee"), decimals=16)
    demand_range = solidity.to_float(rp.call("rocketDAOProtocolSettingsNetwork.getNodeFeeDemandRange"))

    # define vertical lines
    left_border = -demand_range
    left_side = left_border * 1.2
    right_border = demand_range
    right_side = right_border * 1.2

    # left part of the graph
    x_left = np.linspace(left_border, 0, 20)
    left_multiplier = target_fee - min_fee
    func_left = left_multiplier * ((x_left / demand_range) ** 3) + target_fee

    # extend the graph to the left
    x_extended_left = np.linspace(left_side, left_border, 2)
    func_extended_left = x_extended_left / x_extended_left * min_fee

    # right part of the graph
    x_right = np.linspace(0, right_border, 20)
    right_multiplier = max_fee - target_fee
    func_right = right_multiplier * ((x_right / demand_range) ** 3) + target_fee

    # extend the graph to the right
    x_extended_right = np.linspace(right_border, right_side, 2)
    func_extended_right = x_extended_right / x_extended_right * max_fee

    # combine all parts
    x = np.concatenate((x_extended_left, x_left, x_right, x_extended_right))
    func = np.concatenate((func_extended_left, func_left, func_right, func_extended_right))

    # prepare the graph
    fig, ax = plt.subplots()
    ax.set_xlim(left_side, right_side)
    ax.set_ylim(min_fee - 5, max_fee + 5)
    ax.grid(True)

    # labels
    ax.set_xlabel("Node Demand (ETH)")
    ax.set_ylabel("Commission Fee (%)")

    # vertical indicators
    ax.axvline(x=current_node_demand, color='black')
    ax.axvline(x=left_border, color='red')
    ax.axvline(x=right_border, color='green')

    # current commission dot
    ax.plot(current_node_demand, func[np.argmin(np.abs(x - current_node_demand))], 'o', color='black')

    # show current percentage boldly in the middle
    # add out-of-range rectangles
    box_start = None
    if current_node_demand <= left_border:
        box_start = left_side
    elif current_node_demand >= right_border:
        box_start = right_border
    if box_start:
        ax.text(0, max_fee, f"{round(current_commission, 2)}%",
                fontsize=32, color='black', ha='center', va='center', weight='bold')
        ax.add_patch(plt.Rectangle((box_start, min_fee - 5),
                                   right_side - right_border,
                                   max_fee - min_fee + 10,
                                   fill=False,
                                   hatch='///'))

    # draw the function
    ax.plot(x, func, color='blue')

    # store the graph in an file object
    figfile = BytesIO()
    fig.savefig(figfile, format='png')
    figfile.seek(0)
    
    # clear plot from memory
    fig.clf()
    plt.close()

    # store image in cache
    cached_image_commission = current_commission
    cached_image = figfile
    return figfile