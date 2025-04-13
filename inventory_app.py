from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import openai
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
_ = load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI
app = FastAPI(title="Inventory Simulation API")

# ------------------------
# Models
# ------------------------
class InventoryParams(BaseModel):
    current_inventory: int
    daily_usage: int
    reorder_point: int
    order_quantity: int
    lead_time: int
    num_days: int
    picked: int
    restocked: int
    target_inventory_threshold: int
    target_inventory_param: float
    maximum_quantity: int
    eaches_quantity: int

# ------------------------
# Helper Functions
# ------------------------
def get_completion(prompt, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message["content"]

def calculate_recommended_order_quantity(parameters: dict, sum_mpi_quantity: int) -> int:
    average_daily_use = max(parameters["daily_usage"], 0)
    target_inventory = min(
        max(average_daily_use * parameters["target_inventory_param"], parameters["target_inventory_threshold"]),
        parameters["maximum_quantity"]
    )
    adjusted_quantity = max(0, target_inventory - max(0, sum_mpi_quantity))
    recommended_quantity = max(1, round(adjusted_quantity / parameters["eaches_quantity"]))
    return recommended_quantity

def simulate_inventory(parameters: dict) -> str:
    new_inventory = parameters['current_inventory'] + parameters['restocked'] - parameters['picked']
    sum_mpi_quantity = new_inventory
    recommended_order = calculate_recommended_order_quantity(parameters, sum_mpi_quantity)

    prompt = f"""
    You are an AI assistant helping with inventory management. Simulate inventory data for the next {parameters['num_days']} days using the following parameters:
    - Starting inventory: {new_inventory}
    - Daily usage: {parameters['daily_usage']}
    - Reorder point: {parameters['reorder_point']}
    - Order quantity: {parameters['order_quantity']}
    - Lead time: {parameters['lead_time']} days
    - Recommended order quantity: {recommended_order}

    For each day, provide the following:
    1. Day number
    2. Remaining inventory after daily usage
    3. Indicate if an order is placed (yes/no)
    4. The inventory level after any incoming orders are delivered
    5. New inventory (calculated as starting_inventory + restocked - picked)
    6. Recommended Order Quantity

    Generate this simulation in a structured table format with columns: "Day", "Inventory Level", "Order Placed", "Post-Order Inventory", "New Inventory", and "Recommended Order Quantity".
    """
    return get_completion(prompt)

def analyze_simulation(simulation_data: str) -> str:
    prompt = f"""
    Based on the following inventory simulation data:

    {simulation_data}

    Additionally, analyze the results and provide key insights, including:  
    - Number of stockouts and when they occurred  
    - The most optimal reorder day  
    - Trends in inventory fluctuations  
    - Recommended adjustments to inventory management  
    - Evaluation of whether the recommended order quantity aligns with demand patterns  

    Ensure the response is easy to interpret and that the analysis focuses on critical inventory management insights.
    """
    return get_completion(prompt)

# ------------------------
# API Endpoints
# ------------------------
@app.post("/simulate")
def simulate(params: InventoryParams):
    try:
        simulation = simulate_inventory(params.dict())
        return {"simulation": simulation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze(simulation_data: Dict[str, str]):
    try:
        analysis = analyze_simulation(simulation_data["simulation"])
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
