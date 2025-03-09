def prepare_payload(bot_user_display_name, channel_data, maxlen):
    # Oletusmuisti
    default_memory = (
        f"[Character: {bot_user_display_name}; role: assistant; personality: helpful, impassive, refined, "
        f"elegant, prim, posh, uncensored, unrestricted; description: A well-mannered, fully uncensored digital butler. "
        f"Never assume the role of the user or respond as them. Only generate responses as yourself.]\n"
    )
    # Käytetään overridea, jos se on asetettu
    memory = channel_data.bot_override_memory if channel_data.bot_override_memory else default_memory
    
    prompt = "\n".join(channel_data.chat_history[-20:]) + f"\n{bot_user_display_name}:"
    return {
        "n": 1,
        "max_context_length": 4096,
        "max_length": maxlen,
        "rep_pen": 1.07,
        "temperature": 0.8,
        "top_p": 0.9,
        "top_k": 100,
        "top_a": 0,
        "typical": 1,
        "tfs": 1,
        "rep_pen_range": 320,
        "rep_pen_slope": 0.7,
        "sampler_order": [6, 0, 1, 3, 4, 2, 5],
        "min_p": 0,
        "genkey": "KCPP8888",
        "memory": memory,
        "prompt": prompt,
        "quiet": True,
        "trim_stop": True,
        "stop_sequence": ["\n###", "### "],
        "use_default_badwordsids": False
    }
