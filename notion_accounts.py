from notion_client import Client
from datetime import datetime, timedelta
from dataclasses import dataclass
from fonts import *
from api_token import API_TOKEN

#makes a plot with the date in abcissa and the values of array in the y axis. Titles should be put in argument.
def make_plot (date_array, array, y_label, title) : 

    fig, ax = plt.subplots()

    ax.plot(date_array, array, linestyle = "-", color = "#666666")

    title_font = {"fontproperties" : montserrat_font, "color" : "#02452d", 'size' : 20}
    label_font = {"fontproperties" : montserrat_font, "color" : '#02452d', 'size' : 15}

    ax.set_xlabel("date", label_font)
    ax.set_ylabel(y_label, label_font)

    ax.set_title(title, title_font)

    ax.grid(color = "#025839", linestyle = '--', linewidth = 0.5)

#ID-Name matching for the accouts 
accounts = {}
accounts["261a881c-4b67-8141-ad19-d7deaf26f593"] = "Compte courant"
accounts["261a881c-4b67-8175-96c8-d9bec6b37274"] = "Livret A"
accounts["261a881c-4b67-8100-be6d-c49df837dcf0"] = "Livret Jeune"
accounts["261a881c-4b67-81fd-b593-cec56a20d6f1"] = "Especes"
accounts["261a881c-4b67-81c2-ac9a-f350921a93dd"] = "Boursobanque"
accounts["28ba881c-4b67-801d-bb38-dfe7be713f17"] = "Trade Republic (cash)"
accounts["2b8a881c-4b67-80f9-b8c7-e2175202ee63"] = "Trade Republic (PEA)"
accounts["2b8a881c-4b67-8041-a6a7-d9be50d959a0"] = "Trade Republic (Brokerage)"
accounts_list = ["Compte courant", "Livret A", "Livret Jeune", "Especes", "Boursobanque", "Trade Republic (cash)", "Trade Republic (PEA)", "Trade Republic (Brokerage)"]

#Simplyfies the values in the array extracted
def extract_value(prop):
    t = prop["type"]
    v = prop[t]
    if t in ["title", "rich_text"]:
        return v[0]["plain_text"] if v else ""
    elif t == "number":
        return v
    elif t == "select":
        return v["name"] if v else None
    elif t == "multi_select":
        return [opt["name"] for opt in v] if v else []
    elif t == "checkbox":
        return v
    elif t == "date":
        return v["start"] if v else None
    elif t == "relation":
        return v[0]["id"] if v else None
    else:
        return None

#takes all rows of a datasource and puts it in an array of dictonnaries
def fetch_all_rows_from_data_source(notion, data_source_id):
    results = []
    next_cursor = None

    while True:
        params = {"data_source_id": data_source_id}
        if next_cursor:
            params["start_cursor"] = next_cursor

        response = notion.data_sources.query(**params)

        for page in response["results"]:
            props = page["properties"]
            row = {name: extract_value(props[name]) for name in props}
            results.append(row)

        if not response.get("has_more"):
            break

        next_cursor = response.get("next_cursor")

    return results

#Takes all rows of a database and puts it in an array of dictionnaries
def fetch_all_rows_from_database(notion, database_id):
    all_rows = []

    db = notion.databases.retrieve(database_id=database_id)
    data_sources = db.get("data_sources", [])
    if not data_sources:
        raise Exception("No data sources found for this database")

    for ds in data_sources:
        data_source_id = ds["id"]
        print(f"Fetching data from data source '{ds.get('name', 'Unnamed')}' ({data_source_id})...")
        rows = fetch_all_rows_from_data_source(notion, data_source_id)
        all_rows.extend(rows)

    return all_rows

#transforms the array of raw operations in an array of dictionnaries with Nom, Motif entree, Motif sortie, date, compte, and then sorts the array according to the date.
def to_operations_array (raw_array) : 
    print("Converting the raw array into proper operations array...")
    result = []
    for i in range(len(raw_array)) : 
        
        operation = {}
        operation["name"] = raw_array[i]["Nom"]
        operation["in_reason"] = raw_array[i]["Motif entrée"]
        operation["out_reason"] = raw_array[i]["Motif sortie"]
        operation["account"] = accounts[raw_array[i]["Compte"]]
        operation["date"] = datetime.strptime(raw_array[i]["Date"], "%Y-%m-%d")
        operation["amount"] = raw_array[i]["Montant"]

        result.append(operation)

    result = sorted(result, key=lambda op: op["date"])

    return result

#creates an array of dictionnaries with the pogressive amount of money on each account, along with a date. It take the sorted by date array in argument.
def to_progression (array) : 

    print("Building the progression array.")
    #Initialisation of the result array 
    result = [{}]
    result[0]["date"] = array[0]["date"]
    for account in accounts_list :

        result[0][account] = 0
    
    if array[0]["in_reason"] != None : 

        result[0][array[0]["account"]] = array[0]["amount"]
    
    elif array[0]["out_reason"] != None : 

        result[0][array[0]["account"]] = -array[0]["amount"]

    for i in range(1, len(array)) : 
        
        #Copy of the last entry of result
        actual_state = result[-1].copy()

        actual_state["date"] = array[i]["date"]

        if array[i]["in_reason"] != None : 
            actual_state[array[i]["account"]] += array[i]["amount"]
    
        elif array[i]["out_reason"] != None : 
            actual_state[array[i]["account"]] -= array[i]["amount"]

        result.append(actual_state)
        

    return result

#creates an array with the index being the number of days since the creation of the account, and for each day, the dictionnary represents the amount of money on each account. (This dictionnary still contains a date entry)
def to_daily_progression (array) : 
    print("Building the daily progression array.")
    first_day = array[0]["date"]
    last_day = datetime.today()
    actual_date = first_day
    index = 0

    size_result = (last_day - first_day).days
    result = [{} for _ in range(size_result)]

    for i in range(size_result) : 
        
        
        while index != len(array) - 1 and array[index]["date"] == actual_date : 

            index += 1


        result[i] = array[index].copy()
        result[i]["date"] = actual_date
        actual_date = actual_date + timedelta(days = 1)
    
    return result

#Takes just the array of the given dictionnary key
def get_array_values (array, key) : 
    result = []
    for row in array : 
        result.append(row[key])
    return result

def find_index_non_zero(array) : 

    for i in range(len(array)) : 

        if array[i] != 0 : 
            return i

#Returns the end of the array which is non zero
def get_useful_array(array) : 

    index_start = find_index_non_zero(array)
    return array[index_start::]

#Same funcion for the array date
def get_useful_date_array(array, date_array) : 

    index_start = find_index_non_zero(array)
    return date_array[index_start::]

#Takes in argument the the total array, and return of the spending for the selected motive between the start and the ending date included
def get_total_spending_motive(array, date_start, date_end, motive) : 

    result = 0 
    
    for i in range(len(array)) : 

        if array[i]["date"] >= date_start and array[i]["date"] <= date_end and motive == array[i]["out_reason"] :
            
            result += array[i]["amount"]
            
    return result

#Takes in argument the the total array, and return of the earning for the selected motive between the start and the ending date included
def get_total_receiving_motive(array, date_start, date_end, motive) : 

    result = 0 
    
    for i in range(len(array)) : 

        if array[i]["date"] >= date_start and array[i]["date"] <= date_end and motive == array[i]["in_reason"] :

            result += array[i]["amount"]
            
    return result

if __name__ == "__main__":

    notion = Client(auth = API_TOKEN, notion_version="2025-09-03")     
    database_id = "261a881c4b6781cb8e58eb44839ec129"

    all_data = fetch_all_rows_from_database(notion, database_id)

    operations_array = to_operations_array(all_data)
    progression_array = to_progression(operations_array)
    daily_array = to_daily_progression(progression_array)
    
    date = get_array_values(daily_array, "date")
    pea_day_day = get_array_values(daily_array, "Trade Republic (PEA)")
    pea_date_usefull = get_useful_date_array(pea_day_day, date)
    pea_usefull = get_useful_array(pea_day_day)

    plt.plot(pea_date_usefull, pea_usefull)

    plt.savefig("graphs/live_graph.png", dpi=200)
    plt.show()
    plt.close()