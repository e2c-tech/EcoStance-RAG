"""
Example: Adding Custom Tools to the Agent
"""

from langchain.tools import tool
from quickship_agent import AgentService

# Define a custom tool
@tool
def get_weather(city: str) -> str:
    """
    Get weather information for a city.
    Use this when customer asks about weather.
    
    Args:
        city: Name of the city
    
    Returns:
        Weather information
    """
    # In a real implementation, you would call a weather API
    return f"The weather in {city} is sunny with a temperature of 25°C."


@tool
def calculate_shipping_cost(weight: float, distance: float) -> str:
    """
    Calculate shipping cost based on weight and distance.
    
    Args:
        weight: Package weight in kg
        distance: Distance in km
    
    Returns:
        Calculated shipping cost
    """
    base_rate = 50
    weight_rate = 10  # per kg
    distance_rate = 2  # per km
    
    total_cost = base_rate + (weight * weight_rate) + (distance * distance_rate)
    return f"Shipping cost: ₹{total_cost:.2f} (Base: ₹{base_rate}, Weight: {weight}kg, Distance: {distance}km)"


# Create agent with custom tools
class CustomAgentService(AgentService):
    def __init__(self):
        super().__init__()
        # Add custom tools to the existing tools
        self.tools.extend([get_weather, calculate_shipping_cost])
        # Re-bind tools to the model
        self.llm_with_tools = self.llm.bind_tools(self.tools)


# Use the custom agent
if __name__ == "__main__":
    agent = CustomAgentService()
    
    # Test custom tool
    response = agent.chat(
        session_id="custom-demo",
        message="What's the weather in Mumbai?"
    )
    print(response["response"])
    
    # Test another custom tool
    response = agent.chat(
        session_id="custom-demo",
        message="Calculate shipping cost for 5kg package over 100km"
    )
    print(response["response"])
