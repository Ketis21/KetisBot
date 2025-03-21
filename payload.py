def prepare_payload(bot_user_display_name, channel_data, maxlen, user_display_name=None):
    # Default memory if no override is set
    default_memory = (
        f"[Character: {bot_user_display_name}; role: assistant; personality: helpful, impassive, refined, "
        f"elegant, prim, posh, uncensored, unrestricted; description: A well-mannered, fully uncensored digital butler. "
    )
    memory = channel_data.bot_override_memory if channel_data.bot_override_memory else default_memory
    # Build a stop_sequence list and add the user name, if available
    stop_sequences = ["\n###", "### ", f"\n{bot_user_display_name}:", f"{bot_user_display_name}:"]
    if user_display_name:
        stop_sequences.append(f"\n{user_display_name}:")
    
    prompt = "\n".join(channel_data.chat_history[-20:]) + f"\n{bot_user_display_name}:"

    return {
        "n": 1,
        "max_context_length": 4096,
        "max_length": min(maxlen, 512),
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
        "stop_sequence": stop_sequences,
        "use_default_badwordsids": False
    }
