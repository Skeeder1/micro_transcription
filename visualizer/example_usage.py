"""Examples of using the visualizer API."""

from __future__ import annotations

import time

from visualizer.client import VisualizerClient


def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===\n")

    # Create a client
    client = VisualizerClient()

    # Check if server is running
    if not client.ping():
        print("❌ Visualizer server is not running!")
        print("   Start it with: python run_visualizer.py")
        return

    print("✅ Connected to visualizer server\n")

    # Send preview text
    print("Sending preview text...")
    client.send_preview("Bonjour, ceci est un test de transcription.")
    time.sleep(2)

    # Update preview
    print("Updating preview text...")
    client.send_preview("La transcription fonctionne correctement.")
    time.sleep(2)

    # Get status
    print("\nGetting status...")
    status = client.get_status()
    print(f"Status: {status}")

    # Enter sleep mode
    print("\nEntering sleep mode...")
    client.set_state("sleep")
    time.sleep(2)

    # Wake up
    print("Waking up...")
    client.set_state("active")
    time.sleep(1)

    # Clear preview
    print("\nClearing preview...")
    client.clear_preview()

    print("\n✅ Example completed!")


def example_transcription_simulation():
    """Simulate a transcription workflow."""
    print("=== Transcription Simulation Example ===\n")

    client = VisualizerClient()

    if not client.ping():
        print("❌ Visualizer server is not running!")
        return

    print("Starting transcription simulation...\n")

    # Simulate recording and transcription
    transcriptions = [
        "Bonjour",
        "Bonjour, je",
        "Bonjour, je teste",
        "Bonjour, je teste la",
        "Bonjour, je teste la transcription",
        "Bonjour, je teste la transcription en temps réel.",
    ]

    for text in transcriptions:
        print(f"Preview: {text}")
        client.send_preview(text)
        time.sleep(0.5)

    time.sleep(1)

    # Simulate silence -> sleep mode
    print("\n[Silence detected - entering sleep mode]")
    client.set_state("sleep")
    time.sleep(3)

    # Simulate wake up
    print("[Voice detected - waking up]")
    client.set_state("active")
    client.send_preview("Système réactivé")

    time.sleep(1)
    client.clear_preview()

    print("\n✅ Simulation completed!")


def example_error_handling():
    """Example with error handling."""
    print("=== Error Handling Example ===\n")

    client = VisualizerClient()

    # Try to send preview even if server is down
    print("Attempting to send preview...")
    success = client.send_preview("Test message")

    if success:
        print("✅ Preview sent successfully")
    else:
        print("❌ Failed to send preview (server may be down)")

    # Try to get status
    print("\nAttempting to get status...")
    status = client.get_status()

    if status:
        print(f"✅ Status: {status}")
    else:
        print("❌ Failed to get status")


def example_convenience_functions():
    """Example using convenience functions."""
    print("=== Convenience Functions Example ===\n")

    from visualizer import client

    if not client.ping():
        print("❌ Visualizer server is not running!")
        return

    print("Using convenience functions...\n")

    # These functions automatically use a default client instance
    client.send_preview("Using convenience functions")
    time.sleep(1)

    status = client.get_status()
    print(f"Status: {status}")

    client.set_state("sleep")
    time.sleep(1)

    client.set_state("active")
    time.sleep(1)

    client.send_preview("All done!")

    print("\n✅ Example completed!")


def main():
    """Run all examples."""
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Transcription Simulation", example_transcription_simulation),
        ("Error Handling", example_error_handling),
        ("Convenience Functions", example_convenience_functions),
    ]

    print("\n" + "=" * 60)
    print("Visualizer Client Examples")
    print("=" * 60)
    print("\nMake sure the visualizer server is running:")
    print("  python run_visualizer.py\n")

    for i, (name, func) in enumerate(examples, 1):
        print(f"\n\n{'=' * 60}")
        print(f"Example {i}/{len(examples)}: {name}")
        print("=" * 60 + "\n")

        try:
            func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

        if i < len(examples):
            input("\n\nPress Enter to continue to next example...")

    print("\n\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
