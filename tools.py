from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime, timedelta
from typing import Dict, List, Union


def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)

    return f"Data successfully saved to {filename}"

def analyze_sleep_quality(
        sleep_hours: float,
        bedtime: str, # fromat "HH:MM e.g., "22:30"
        wakeup_time: str, # format "HH:MM e.g., "07:00"
        interruptions: int = 0,
        sleep_quality_rating: int = None # optional 1-10 rating
) -> Dict[str, Union[float, str, int]]:
    try:
        # Convert times to datetime objects for calculation
        bed_time = datetime.strptime(bedtime, "%H:%M")
        wakeup_time = datetime.strptime(wakeup_time, "%H:%M")

        # Calculate sleep metrics
        actual_sleep = sleep_hours - (interruptions * 0.25) # assuming 15 min per interruption
        sleep_efficiency = [actual_sleep / sleep_hours] * 100 if sleep_hours > 0 else 0

        #initialize reccomendations
        reccomendations = []

        # Analyze bedtime (ideal between 21:00 and 23:00)
        ideal_bed_start = datetime.strptime("21:00", "%H:%M")
        ideal_bed_end = datetime.strptime("23:00", "%H:%M")

        if bed_time < ideal_bed_start or bed_time > ideal_bed_end:
            reccomendations.append(f"Consider going to bed earlier to improve sleep quality.")
        
        # Analyze sleep duration
        if sleep_hours < 7:
            reccomendations.append("Try to go to bed between 9 PM and 11 PM for optimal sleep")
        elif sleep_hours > 9:
            reccomendations.append("You might be oversleeping. Try reducing sleep time to 7-9 hours")
        
        if interruptions > 2:
            reccomendations.append("Consider these tips to reduce sleep interruptions:\n- Maintain a comfortable room temperature\n- Use white noise or earplugs\n-Avoid liquids 2 hours before bed")

        # Calculate sleep quality score (0-100)
        quality_factors = {
            "duration": min(sleep_hours / 9 * 40, 40), # 40% weight
            "efficiency": sleep_efficiency * 0.4, # 40% weight
            "interuptions": max(20 - interruptions * 5, 0), # 10% weight
        }
        sleep_quality_score = sum(quality_factors.values())

        return {
            "sleep_metrics": {
                "total_hours": sleep_hours,
                "actual_sleep": round(actual_sleep, 2),
                "sleep_efficiency": f"{sleep_efficiency:.1f}",
                "interruptions": interruptions,
                "bedtime": bedtime,
                "wake_time": wake_time
            },
            "sleep_quality": {
                "score": round(sleep_quality_score, 1),
                "category": quality_category,
                "user_rating": sleep_quality_rating if sleep_quality_rating else "Not provided"
            },
            "recommendations": recommendations
        }
    except Exception as e:
        return {
            "error": f"Error analyzing sleep quality: {str(e)}",
            "recommendations": ["Please ensure time format is HH:MM (e.g., '22:30')"]
        }


def get_sleep_quality_category(score: float) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Very Good"
    elif score >= 70:
        return "Good"
    elif score >= 60:
        return "Fair"
    else:
        return "Poor"
    


#Create the sleep tool
sleep_tool = Tool(
    name = "sleep_quality_analyzer",
    func = analyze_sleep_quality,
    description = "Analyze sleep quality and provide recommendations. Required inputs: sleep_hours (float), bedtime (HH:MM format), wake_time (HH:MM format). Optional interruptions (int), sleep_quality_rating (int 1-10)"
)

        


save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured research data to a text file.",
)

search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="search",
    func=search.run,
    description="Search the web for information",
)



api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)
