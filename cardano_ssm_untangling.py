
##########################################################################################
##########################################################################################
##########################################################################################
# This function takes a list where each element is a tuple consisting of an address (string), an ADA value (integer), 
# and a list of pairs (MA name and MA value as an integer). It returns a dictionary where each address is unique and 
# its value is a dictionary. This nested dictionary includes the sum of the ADA value and the sum of 
# all MA values associated with the same MA name for that address.
def unify_ADA_and_MAs_by_address(input_list):
    result = {}
    for address, ada_value, MAs in input_list:
        if address not in result:
            result[address] = {"TX_ADA_total": 0}

        # Add the ADA value to the total for this address
        result[address]["TX_ADA_total"] += ada_value

        for ma_name, ma_value in MAs:
            if ma_name in result[address]:
                result[address][ma_name] += ma_value
            else:
                result[address][ma_name] = ma_value

    return result



##########################################################################################
# For each address that exists in both dictionaries, this function subtracts the smaller values
# for all keys (including ADA_total and MA values) from both dictionaries.
def subtract_smaller_values(dict1, dict2):
    common_addresses = set(dict1.keys()) & set(dict2.keys())

    for address in common_addresses:
        common_keys = set(dict1[address].keys()) & set(dict2[address].keys())

        for key in common_keys:
            smaller_value = min(dict1[address][key], dict2[address][key])
            dict1[address][key] -= smaller_value
            dict2[address][key] -= smaller_value

    # Removes any address from dict1 and dict2 if the values for all keys (ADA_total, MA1, MA2, ...) in that address are zero.
    def remove_if_all_zeros(dictionary):
        addresses_to_remove = [address for address, values in dictionary.items() if all(value == 0 for value in values.values())]
        for address in addresses_to_remove:
            del dictionary[address]

    remove_if_all_zeros(dict1)
    remove_if_all_zeros(dict2)

    return list(dict1.items()), list(dict2.items())



##########################################################################################
def get_elements_at_set_bits(input_list, number):
    result = []
    index = 0

    while number > 0:
        # Check if the least significant bit of the number is set
        if number & 1:
            # Check if the index is within the bounds of the list
            if index < len(input_list):
                result.append(input_list[index])

        # Shift the number to the right to check the next bit
        number >>= 1
        # Increment the index to move to the next element in the list
        index += 1

    return result



##########################################################################################
def calculate_sums_tx_inout_subset(subset):
    sums = {}
    for _, assets in subset:
        for key, value in assets.items():
            sums[key] = sums.get(key, 0) + value
    return sums



##########################################################################################
def check_if_connectable_subsets(input_subset, output_subset, dict_fee_mints):
    # Calculate sums for input and output subsets
    input_sums = calculate_sums_tx_inout_subset(input_subset)
    output_sums = calculate_sums_tx_inout_subset(output_subset)

    # Compare sums with consideration of dict_fee_mints
    all_valid = True
    all_keys = set(input_sums.keys()).union(output_sums.keys()).union(dict_fee_mints.keys())
    for key in all_keys:
        input_sum = input_sums.get(key, 0)
        output_sum = output_sums.get(key, 0)

        if key == 'TX_ADA_total':
            fee           = dict_fee_mints[key][0]
            withdraw_list = dict_fee_mints[key][1]
            all_withdraw_subsets = [comb for r in range(len(withdraw_list) + 1) for comb in combinations(withdraw_list, r)]  # "r = 0" means: no withdrawal!
            if all (not (output_sum < input_sum + sum(subset) < (output_sum - fee)) for subset in all_withdraw_subsets):     # "fee" cannot be "0" in a sub-transaction
                all_valid = False;
                break;
        else:
            mint = dict_fee_mints.get(key, 0)
            if not ( min(output_sum, output_sum - mint) <= input_sum <= max(output_sum, output_sum - mint) ):
                all_valid = False;
                break;

    return all_valid;


##########################################################################################
def find_all_connectable_pairs(list_ins, list_outs, dict_fee_mints):
    valid_pairs = []
    
    for i in range(1, 1 << len(list_ins)):
        for j in range(1, 1 << len(list_outs)):
            
            # We do not consider the original transaction case (i.e., "all input elements" and "all output elements")
            if (i == (1 << len(list_ins))-1) and (j == (1 << len(list_outs))-1):
                break;

            ins_subset  = get_elements_at_set_bits(list_ins, i)
            outs_subset = get_elements_at_set_bits(list_outs, j)
            
            if (check_if_connectable_subsets(ins_subset, outs_subset, dict_fee_mints)):
                valid_pairs.append((i,j))
                
    return valid_pairs;


##########################################################################################
# check if for all ADA and MAs we have "input_sum == output_sum - fee_mint":
def check_if_TX_is_complete(list_ins, list_outs, dict_fee_mints):
    # Calculate sums for input and output subsets
    input_sums = calculate_sums_tx_inout_subset(list_ins)
    output_sums = calculate_sums_tx_inout_subset(list_outs)

    # Compare sums with consideration of dict_fee_mints
    all_valid = True
    all_keys = set(input_sums.keys()).union(output_sums.keys()).union(dict_fee_mints.keys())
    for key in all_keys:
        input_sum = input_sums.get(key, 0)
        output_sum = output_sums.get(key, 0)
        if key == 'TX_ADA_total':
            #fee_mint = sum(dict_fee_mints[key])
            fee_mint = sum(n for e in dict_fee_mints[key] for n in (e if isinstance(e, list) else [e]))
        else:
            fee_mint = dict_fee_mints.get(key, 0)

        # Check the specified condition
        if (input_sum != output_sum - fee_mint):
            all_valid = False
            break

    return all_valid


##########################################################################################
# Check if there is a duplicate subset of inputs/outputs in connected pairs:
def check_if_ambiguous_by_lemma_1(conn_pairs_list):
    first_elements  = set()
    second_elements = set()

    for first, second in conn_pairs_list:
        if (first in first_elements) or (second in second_elements):
            return True;
        
        first_elements.add(first)
        second_elements.add(second)

    return False;


##########################################################################################
def calculate_minimal_pairs(conn_pairs_list):
    n = len(conn_pairs_list)
    
    # Initialize a boolean list with the same length as conn_pairs_list
    remove_flags = [False] * n

    for i in range(n):
        a1, b1 = conn_pairs_list[i]

        # Avoid redundant checks and ensure not already flagged for removal
        if not remove_flags[i]:
            for j in range(i+1, n):
                a2, b2 = conn_pairs_list[j]

                if   (a1 & a2 == a1) and (b1 & b2 == b1):  # Check if (a1,b1) ⊆ (a2,b2)
                    remove_flags[j] = True
                elif (a1 & a2 == a2) and (b1 & b2 == b2):  # Check if (a2,b2) ⊆ (a1,b1)
                    remove_flags[i] = True

    # Create a new list excluding pairs flagged for removal
    minimal_pairs = [pair for index, pair in enumerate(conn_pairs_list) if not remove_flags[index]]

    return minimal_pairs;


##########################################################################################
def check_if_ambiguous_by_lemma_2(min_conn_pairs_list):
    n = len(min_conn_pairs_list)

    for i in range(n):
        a1, b1 = min_conn_pairs_list[i]
        for j in range(i+1, n):
            a2, b2 = min_conn_pairs_list[j]

            if (a1 & a2 != 0) or (b1 & b2 != 0): # Check if (a1 ∩ a2 ≠ ∅) OR (b1 ∩ b2 ≠ ∅) 
                return True;

    return False;


##########################################################################################
# The definition of each category is as follows:
#    1. 'TX_not_complete': We have “Input + fee + withdraw != output” - e.g. stake address deregistration
#    2. 'TX_no_input_or_output': After simplification, the TX has 0 inputs/outputs - e.g. calling a smart contract
#    3. 'TX_regular': After simplification, the TX has only a single input/output - This category includes the majority of the TXs
#    4. 'TX_complex': After simplification, there are still common addresses in the inputs and outputs list. For example, this happens when there is an address whose ADA has decreased but its FT1 has increased. Then after subtracting the ADA and FT1 from the address on both sides (inputs and outputs), both the “input vector” of that address and its “output vector” will be non-zero.
#    5. 'TX_size_limit': After simplification, the TX has more than 10 different input/output addresses
#    6. 'TX_simple': Non splittable
#    7. 'TX_ambiguous': Splittable in multiple ways
#    8. 'TX_separable': Splittable in a unique way
#    9. 'TX_not_classified': None of the above categories (count = 0)

def classify_transaction(list_ins, list_outs, dict_fee_mints):

    # Find the common addresses using set intersection
    addresses_in  = {pair[0] for pair in list_ins}
    addresses_out = {pair[0] for pair in list_outs}
    common_addresses = addresses_in.intersection(addresses_out)

    if not check_if_TX_is_complete(list_ins, list_outs, dict_fee_mints): # It means that for some ADA/MAs we have "input_sum != output_sum - fee_mint".
        return 'TX_not_complete';

    elif (len(list_ins) == 0 or len(list_outs) == 0):
        return 'TX_no_input_or_output';

    elif (len(list_ins) == 1 or len(list_outs) == 1):
        return 'TX_regular';

    elif (len(common_addresses) > 0): # It means that some addresses have received some tokens and have spent some other tokens in the same transaction.
        return 'TX_complex'; 

    elif (len(list_ins) + len(list_outs) + len(dict_fee_mints['TX_ADA_total'][1]) > 10): # It means that there will be too many combinations of input/output/withdrawal subsets.
        return 'TX_size_limit';


    # Find all connectable pairs
    connectable_pairs_list = find_all_connectable_pairs(list_ins, list_outs, dict_fee_mints)

    if (connectable_pairs_list == []):
        return 'TX_simple';

    # Check "Lemma 1" for "connectable pairs":
    if (check_if_ambiguous_by_lemma_1(connectable_pairs_list)):
        return 'TX_ambiguous';

    # Check "Lemma 2" only for "minimal connectable pairs":
    minimal_connectable_pairs_list = calculate_minimal_pairs(connectable_pairs_list) # Calculate minimal connectable pairs:
    if (check_if_ambiguous_by_lemma_2(minimal_connectable_pairs_list)):
        return 'TX_ambiguous';


    # If neither Lemma 1 nor Lemma 2 recognize the TX as ambiguous, then the TX is "separable":
    return 'TX_separable';


##########################################################################################
