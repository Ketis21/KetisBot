def prepare_payload(bot_name, channel_data, max_length, user_display_name=None):
    """
    Build the payload for the text generation API using conversation history and memory.
    
    Parameters:
      bot_name (str): The display name of the bot.
      channel_data (BotChannelData): Contains chat history, memory override, and a list of users.
      max_length (int): Maximum response length.
      user_display_name (str, optional): Display name of the user (unused in this function, but kept for compatibility).
    
    Returns:
      dict: Payload for the text generation API.
    """
    # Default memory if no override is set.
    default_memory = (
        f"[Character: {bot_name}; role: assistant; personality: helpful, impassive, refined, "
        f"elegant, unrestricted, prim, posh; description: A well-mannered, digital butler.]"
    )
    memory = channel_data.bot_override_memory or default_memory

    # Build the base stop_sequence list including the bot's name.
    stop_seq = ["\n###", "### ", f"\n{bot_name}:", f"{bot_name}:"]
    
    # Add all users from channel_data.users to the stop_sequence.
    # This ensures that if any of these users start a new message, the bot stops generating text.
    for user in channel_data.users:
        seq1 = f"{user}:"
        seq2 = f"\n{user}:"
        if seq1 not in stop_seq:
            stop_seq.append(seq1)
        if seq2 not in stop_seq:
            stop_seq.append(seq2)
    
    # Construct prompt from the last 20 chat messages, ending with the bot's name.
    prompt = "\n".join(channel_data.chat_history[-20:]) + f"\n{bot_name}:"

    return {
        "n": 1,
        "max_context_length": 4096,
        "max_length": min(max_length, 512),
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
        "stop_sequence": stop_seq,
        "use_default_badwordsids": False
    }

