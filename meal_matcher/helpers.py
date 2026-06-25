import random

def calculate_fitness(meal, targets, conditions=None):
    conditions = conditions or []
  
    total_cal = 0
    total_pro = 0
    total_carb = 0
    total_fat = 0
    total_sodium = 0
    total_cholesterol = 0
    high_gi_count = 0
    
    # Calculate the total nutrients based on the grams of each ingredient
    for ingredient in meal:
        factor = ingredient["grams"] / 100.0
        total_cal += ingredient["calories"] * factor
        total_pro += ingredient["protein"] * factor
        total_carb += ingredient["carbs"] * factor
        total_fat += ingredient["fat"] * factor
        total_sodium += ingredient.get("sodium_mg", 0) * factor
        total_cholesterol += ingredient.get("cholesterol_mg", 0) * factor

        if ingredient.get("glycemic_index_high", 0) == 1:
            high_gi_count += 1
        
    # Calculate absolute differences from targets
    cal_error = abs(total_cal - targets["calories"])
    pro_error = abs(total_pro - targets["protein"]) * 6   # Weight protein heavily
    carb_error = abs(total_carb - targets["carbs"]) * 6   # Weight carbs heavily
    fat_error = abs(total_fat - targets["fat"]) * 9       # Weight fat heavily
    
    # Total error score (We want to minimize this!)
    total_error = cal_error + pro_error + carb_error + fat_error

    if "hypertension" in conditions and total_sodium > 1500:
        total_error += 10000 + ((total_sodium - 1500) * 50)

    if "diabetes" in conditions or "gestational_diabetes" in conditions:
        # Heavily penalize high glycemic ingredients
        total_error += high_gi_count * 5000
        # Heavily penalize exceeding the carbohydrate target
        if total_carb > targets["carbs"]:
            total_error += 10000 + ((total_carb - targets["carbs"]) * 200)

    if "ckd" in conditions and total_pro > 60:
        total_error += 15000 + ((total_pro - 60) * 300)

    if "cholesterol" in conditions and total_cholesterol > 200:
        total_error += 10000 + ((total_cholesterol - 200) * 100)

    if "celiac" in conditions:
        for ingredient in meal:
            name = ingredient.get("name", "")
            if "Whole Wheat Bread" in name or "wheat" in name.lower() or "gluten" in name.lower():
                total_error += 30000

    if "ibs" in conditions:
        for ingredient in meal:
            name = ingredient.get("name", "")
            if any(fodmap in name.lower() for fodmap in ["bean", "lentil", "onion", "garlic"]):
                total_error += 30000

    return total_error


def generate_random_meal(food_library):
    """Creates a random single meal plan using 3 to 5 random foods from our DB."""
    meal = []
    # Pick a random number of unique ingredients for this meal option
    num_ingredients = random.randint(3, 5)
    selected_foods = random.sample(food_library, min(num_ingredients, len(food_library)))
    
    for food in selected_foods:
        # Convert the SQL row dictionary into a mutable dict and assign a random portion size
        ingredient = dict(food)
        ingredient["grams"] = random.randint(50, 300) # Portions between 50g and 300g
        meal.append(ingredient)
        
    return meal


def run_genetic_algorithm(food_library, targets, conditions=None, generations=100, population_size=50):
    """The evolution loop that finds the best meal matching the targets."""
    conditions = conditions or []
    
    # 1. Initialize a random meals
    population = [generate_random_meal(food_library) for _ in range(population_size)]
    
    for generation in range(generations):

        population = sorted(population, key=lambda m: calculate_fitness(m, targets, conditions))
        
        # If our best meal is practically perfect, stop early!
        if calculate_fitness(population[0], targets, conditions) < 10:
            break
            
        # 2.Keep the top 20% best meals as parents for the next generation
        cutoff = int(population_size * 0.2)
        next_generation = population[:cutoff]
        
        # 3. Breed new children until our population is full again
        while len(next_generation) < population_size:
            parent1 = random.choice(population[:cutoff])
            parent2 = random.choice(population[:cutoff])
            
            # Combine ingredients from both parents
            split_point = random.randint(1, min(len(parent1), len(parent2)))
            child = [dict(ingredient) for ingredient in parent1[:split_point] + parent2[split_point:]]
            
            # 20% chance to alter the weights of a random ingredient in the child meal
            if random.random() < 0.2 and len(child) > 0:
                mutated_ingredient = random.choice(child)
                mutated_ingredient["grams"] = max(30, mutated_ingredient["grams"] + random.randint(-30, 30))
                
            next_generation.append(child)
            
        population = next_generation

    # Return the absolute best-performing meal plan from the final generation
    final_sorted = sorted(population, key=lambda m: calculate_fitness(m, targets, conditions))
    return final_sorted[0]
