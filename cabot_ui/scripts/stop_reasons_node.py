#!/usr/bin/env python3

import rclpy
from rclpy.time import Duration
from rclpy.node import Node
import tf2_ros
import nav_msgs.msg
import std_msgs.msg
import geometry_msgs.msg
import nav2_msgs.msg
import nav2_msgs.action
import cabot_msgs.msg
import people_msgs.msg
import threading

from cabot_ui.stop_reasoner import StopReasonFilter, StopReasoner
from cabot_ui.event import NavigationEvent
from cabot_ui.cabot_rclpy_util import CaBotRclpyUtil


reasoner = None
stop_reason_pub = None
event_pub = None


def main():
    global reasoner, stop_reason_pub, event_pub
    ODOM_TOPIC = "/cabot/odom_raw"
    EVENT_TOPIC = "/cabot/event"
    CMD_VEL_TOPIC = "/cmd_vel"
    PEOPLE_SPEED_TOPIC = "/cabot/people_speed"
    TF_SPEED_TOPIC = "/cabot/tf_speed"
    TOUCH_SPEED_TOPIC = "/cabot/touch_speed_switched"
    # NAVIGATE_TO_POSE_GOAL_TOPIC = "/navigate_to_pose/goal"
    NAVIGATE_TO_POSE_RESULT_TOPIC = "/navigate_to_pose/result"
    LOCAL_PREFIX = "/local"
    REPLAN_REASON_TOPIC = "/replan_reason"
    CURRENT_FRAME_TOPIC = "/current_frame"

    rclpy.init()
    node = Node("stop_reason_node")
    CaBotRclpyUtil.initialize(node)
    tf_buffer = tf2_ros.Buffer(Duration(seconds=10), node)
    tf_listener = tf2_ros.TransformListener(tf_buffer, node)
    reasoner = StopReasoner(tf_listener)

    stop_reason_pub = node.create_publisher(cabot_msgs.msg.StopReason, "/stop_reason", 10)
    event_pub = node.create_publisher(std_msgs.msg.String, "/cabot/event", 10)

    node.create_subscription(nav_msgs.msg.Odometry, ODOM_TOPIC, odom_callback, 10)
    node.create_subscription(std_msgs.msg.String, EVENT_TOPIC, event_callback, 10)
    node.create_subscription(geometry_msgs.msg.Twist, CMD_VEL_TOPIC, cmd_vel_callback, 10)
    node.create_subscription(std_msgs.msg.Float32, PEOPLE_SPEED_TOPIC, people_speed_callback, 10)
    node.create_subscription(std_msgs.msg.Float32, TF_SPEED_TOPIC, tf_speed_callback, 10)
    node.create_subscription(std_msgs.msg.Float32, TOUCH_SPEED_TOPIC, touch_speed_callback, 10)
    # TODO
    # goal_sub = node.create_subscription(nav2_msgs.action.NavigateToPose.ActionGoal, NAVIGATE_TO_POSE_GOAL_TOPIC, goal_callback, 10)
    node.create_subscription(nav2_msgs.action.NavigateToPose.Result, NAVIGATE_TO_POSE_RESULT_TOPIC, result_callback, 10)
    # TODO
    # local_goa_sub = node.create_subscription(nav2_msgs.action.NavigateToPoseActionGoal, LOCAL_PREFIX+NAVIGATE_TO_POSE_GOAL_TOPIC, goal_callback, 10)
    node.create_subscription(nav2_msgs.action.NavigateToPose.Result, LOCAL_PREFIX+NAVIGATE_TO_POSE_RESULT_TOPIC, result_callback, 10)
    node.create_subscription(people_msgs.msg.Person, REPLAN_REASON_TOPIC, replan_reason_callback, 10)
    node.create_subscription(std_msgs.msg.String, CURRENT_FRAME_TOPIC, current_frame_callback, 10)

    node.create_timer(0.1, timer_callback)

    rclpy.spin(node)


def timer_callback():
    update()

lock = threading.Lock()
stop_reason_filter = StopReasonFilter()


def update():
    with lock:
        global prev_code, prev_duration
        (duration, code) = reasoner.update()
        stop_reason_filter.update(duration, code)
        (duration, code) = stop_reason_filter.event()
        print(duration, code)
        if code:
            msg = cabot_msgs.msg.StopReason()
            msg.header.stamp = CaBotRclpyUtil.now().to_msg()
            msg.reason = code.name
            msg.duration = duration
            stop_reason_pub.publish(msg)
        (duration, code) = stop_reason_filter.summary()
        if code:
            event = NavigationEvent("stop-reason", code.name)
            msg = std_msgs.msg.String()
            msg.data = str(event)
            event_pub.publish(msg)
            CaBotRclpyUtil.info("%.2f, %s, %.2f", CaBotRclpyUtil.Time.now().nanoseconds/1e9, code.name, duration)
        stop_reason_filter.conclude()


def odom_callback(msg):
    reasoner.input_odom(msg)


def event_callback(msg):
    reasoner.input_event(msg)


def goal_callback(msg):
    reasoner.input_goal_topic(msg)


def result_callback(msg):
    reasoner.input_result_topic(msg)


def cmd_vel_callback(msg):
    reasoner.input_cmd_vel(msg)


def people_speed_callback(msg):
    reasoner.input_people_speed(msg)


def tf_speed_callback(msg):
    pass


def touch_speed_callback(msg):
    reasoner.input_touch_speed(msg)


def replan_reason_callback(msg):
    reasoner.input_replan_reason(msg)


def current_frame_callback(msg):
    reasoner.input_current_frame(msg)


if __name__ == "__main__":
    main()
