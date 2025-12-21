"""
Demo refresh automation script for Cloud Cost Optimizer.

Automates the complete demo refresh process:
1. Clears and reseeds synthetic data
2. Retrains the ML model

Usage:
    python -m scripts.refresh_demo_data
    python -m scripts.refresh_demo_data --force  # Skip confirmation
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(command, description, input_text=None):
    """
    Run a command and stream its output in real-time.
    
    Args:
        command: List of command arguments
        description: Description of what's being run
        input_text: Optional text to send to stdin (for confirmations)
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"🔄 {description}")
    print(f"{'=' * 60}\n")
    
    try:
        # Run command and stream output in real-time
        stdin = subprocess.PIPE if input_text else None
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=stdin,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        
        # Send input if provided
        if input_text:
            process.stdin.write(input_text)
            process.stdin.close()
        
        # Stream output line by line
        for line in process.stdout:
            print(line, end='')
        
        # Wait for completion
        process.wait()
        
        if process.returncode != 0:
            print(f"\n❌ Error: {description} failed with exit code {process.returncode}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error running {description}: {e}")
        return False


def main():
    """Main function to orchestrate the demo refresh process."""
    parser = argparse.ArgumentParser(
        description="Refresh demo data and retrain ML model"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (useful for automation)",
    )
    args = parser.parse_args()
    
    # Confirmation prompt (unless --force)
    if not args.force:
        print("\n" + "=" * 60)
        print("⚠️  DEMO REFRESH PROCESS")
        print("=" * 60)
        print("This will:")
        print("  1. Clear and reseed all demo data")
        print("  2. Retrain the ML model")
        print("\nThis process may take a few minutes.")
        print("=" * 60)
        response = input("\nDo you want to continue? (Y/n): ").strip().lower()
        
        if response not in ['y', 'yes', '']:
            print("\n❌ Refresh cancelled.")
            sys.exit(0)
    
    # Start timing
    start_time = time.time()
    
    # Get the backend directory path
    backend_dir = Path(__file__).parent.parent
    python_executable = sys.executable
    
    # Step 1: Seed demo data
    print("\n" + "=" * 60)
    print("📊 STEP 1: Seeding Demo Data")
    print("=" * 60)
    
    seed_command = [
        python_executable,
        "-m",
        "scripts.seed_demo_data",
    ]
    
    # Auto-confirm the seed script if we already confirmed at the top level
    # The seed script will show its own confirmation prompt, so we'll auto-answer "y"
    if not run_command(seed_command, "Seeding demo data", input_text="y\n"):
        print("\n" + "=" * 60)
        print("❌ Demo refresh failed at step 1: Seeding data")
        print("=" * 60)
        sys.exit(1)
    
    # Step 2: Train ML model
    print("\n" + "=" * 60)
    print("🤖 STEP 2: Training ML Model")
    print("=" * 60)
    
    train_command = [
        python_executable,
        "-m",
        "app.ml.train_model",
    ]
    
    if not run_command(train_command, "Training ML model"):
        print("\n" + "=" * 60)
        print("❌ Demo refresh failed at step 2: Training model")
        print("=" * 60)
        sys.exit(1)
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Success summary
    print("\n" + "=" * 60)
    print("✅ Demo data reseeded and ML model retrained successfully!")
    print("=" * 60)
    print(f"\n⏱  Completed in {elapsed_time:.2f}s")
    print("\n📝 Next steps:")
    print("   1. Restart the backend: uvicorn app.main:app --reload")
    print("   2. Reload the frontend to view updated recommendations")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

